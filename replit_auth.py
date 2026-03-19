import jwt
import os
import uuid
from urllib.parse import urlencode

from flask import g, session, redirect, request, url_for
from flask_dance.consumer import OAuth2ConsumerBlueprint, oauth_authorized, oauth_error
from flask_dance.consumer.storage import BaseStorage
from flask_login import login_user, logout_user

from models import db, User


class SessionTokenStorage(BaseStorage):
    def get(self, blueprint):
        return session.get("replit_oauth_token")

    def set(self, blueprint, token):
        session["replit_oauth_token"] = token
        session.modified = True

    def delete(self, blueprint):
        session.pop("replit_oauth_token", None)


def make_replit_blueprint():
    repl_id = os.environ.get("REPL_ID", "")
    issuer_url = os.environ.get("ISSUER_URL", "https://replit.com/oidc")

    replit_bp = OAuth2ConsumerBlueprint(
        "replit_auth",
        __name__,
        client_id=repl_id,
        client_secret=None,
        base_url=issuer_url,
        authorization_url_params={"prompt": "login consent"},
        token_url=issuer_url + "/token",
        token_url_params={"auth": (), "include_client_id": True},
        auto_refresh_url=issuer_url + "/token",
        auto_refresh_kwargs={"client_id": repl_id},
        authorization_url=issuer_url + "/auth",
        use_pkce=True,
        code_challenge_method="S256",
        scope=["openid", "profile", "email", "offline_access"],
        storage=SessionTokenStorage(),
    )

    @replit_bp.before_app_request
    def set_browser_session_key():
        if "_browser_session_key" not in session:
            session["_browser_session_key"] = uuid.uuid4().hex
        session.modified = True
        g.browser_session_key = session["_browser_session_key"]

    @replit_bp.route("/logout")
    def logout():
        del replit_bp.token
        logout_user()
        end_session_endpoint = issuer_url + "/session/end"
        params = urlencode({
            "client_id": repl_id,
            "post_logout_redirect_uri": request.url_root,
        })
        return redirect(f"{end_session_endpoint}?{params}")

    @oauth_authorized.connect_via(replit_bp)
    def replit_logged_in(blueprint, token):
        user_claims = jwt.decode(
            token["id_token"], options={"verify_signature": False}
        )
        replit_sub = str(user_claims.get("sub", ""))
        email = user_claims.get("email")

        user = None

        if replit_sub:
            user = User.query.filter_by(replit_sub=replit_sub).first()

        if not user and email:
            user = User.query.filter_by(email=email).first()
            if user:
                user.replit_sub = replit_sub
                db.session.commit()

        if not user:
            base_username = (
                email.split("@")[0] if email else f"user_{replit_sub[:8]}"
            )
            username = base_username
            counter = 1
            while User.query.filter_by(username=username).first():
                username = f"{base_username}{counter}"
                counter += 1

            user = User(
                username=username,
                email=email or f"{replit_sub}@replit.user",
                password="",
                replit_sub=replit_sub,
            )
            db.session.add(user)
            db.session.commit()

        login_user(user)
        blueprint.token = token

        next_url = session.pop("next_url", None)
        if next_url:
            return redirect(next_url)
        return redirect(url_for("dashboard"))

    @oauth_error.connect_via(replit_bp)
    def replit_error(blueprint, error, error_description=None, error_uri=None):
        return redirect(url_for("login"))

    return replit_bp
