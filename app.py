import os
from flask import Flask, render_template, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager

from config import Config
from database import db


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Ensure upload directory exists
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # Extensions
    db.init_app(app)
    JWTManager(app)
    CORS(app)

    # Attach Activity Logging Middleware
    from services.logging_service import setup_logging_middleware
    setup_logging_middleware(app)

    # Register blueprints
    from routes.auth import auth_bp
    from routes.admin import admin_bp
    from routes.student import student_bp
    from routes.company import company_bp
    from routes.ml import ml_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(company_bp)
    app.register_blueprint(ml_bp)

    # Create tables
    with app.app_context():
        import models  # noqa: F401 — ensures all models are registered
        db.create_all()

        # Seed default Admin tracking record if admin user exists but the tracking record doesn't
        try:
            from models.user import User
            from models.tracking import AdminTable
            admin = User.query.filter_by(username="admin").first()
            if admin:
                admin_record = AdminTable.query.filter_by(user_id=admin.id).first()
                if not admin_record:
                    admin_record = AdminTable(user_id=admin.id, username=admin.username, password_hash=admin.password_hash)
                    db.session.add(admin_record)
                    db.session.commit()
                    print("[DB] Synced AdminTable tracking record.")
        except Exception as e:
            print(f"[DB] Could not sync AdminTable: {e}")

        # Auto-train ML models if not already trained
        try:
            from services.ml_service import train_models
            if not os.path.exists(os.path.join(os.path.dirname(__file__), "ml_models", "placement_classifier.pkl")):
                print("[ML] Training models on startup...")
                metrics = train_models()
                print(f"[ML] Classifier accuracy: {metrics['classifier_accuracy']}%")
                print(f"[ML] Regressor R² score: {metrics['regressor_r2_score']}%")
        except Exception as e:
            print(f"[ML] Could not auto-train models: {e}")

    # ─── Page routes ───

    @app.route("/")
    def index():
        return render_template("login.html")

    @app.route("/dashboard")
    def dashboard():
        return render_template("dashboard.html")

    @app.route("/uploads/<path:filename>")
    def serve_upload(filename):
        return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=5000)
