-- ---------------------------------------------------------------------
-- Loan Eligibility Prediction System — MySQL 8.x schema
--
-- Option A (recommended): set DATABASE_URL in .env and let SQLAlchemy
-- create the tables with `flask --app app init-db`.
-- Option B: run this file manually in MySQL Workbench or the mysql CLI.
--
--   mysql -u root -p < database/schema.sql
--
-- The application also works with SQLite by default (no setup required).
-- ---------------------------------------------------------------------

CREATE DATABASE IF NOT EXISTS loan_eligibility
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE loan_eligibility;

CREATE TABLE IF NOT EXISTS users (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT,
  full_name VARCHAR(120) NOT NULL,
  email VARCHAR(190) NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  role VARCHAR(20) NOT NULL DEFAULT 'user',
  created_at DATETIME NOT NULL,
  last_login_at DATETIME NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_users_email (email),
  KEY ix_users_role (role)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS applications (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT,
  user_id INT UNSIGNED NOT NULL,
  applicant_name VARCHAR(120) NOT NULL,

  Gender VARCHAR(10) NOT NULL,
  Married VARCHAR(3) NOT NULL,
  Dependents VARCHAR(3) NOT NULL,
  Education VARCHAR(20) NOT NULL,
  Self_Employed VARCHAR(3) NOT NULL,
  ApplicantIncome DOUBLE NOT NULL,
  CoapplicantIncome DOUBLE NOT NULL,
  LoanAmount DOUBLE NOT NULL,
  Loan_Amount_Term INT NOT NULL,
  Credit_History TINYINT NOT NULL,
  Property_Area VARCHAR(12) NOT NULL,

  prediction TINYINT NOT NULL,
  eligibility_probability DOUBLE NOT NULL,
  prediction_confidence DOUBLE NOT NULL,
  model_name VARCHAR(50) NOT NULL,
  created_at DATETIME NOT NULL,

  PRIMARY KEY (id),
  KEY ix_applications_user_id (user_id),
  KEY ix_applications_created_at (created_at),
  KEY ix_applications_prediction (prediction),
  KEY ix_applications_user_created (user_id, created_at),
  KEY ix_applications_prediction_created (prediction, created_at),
  CONSTRAINT fk_applications_user
    FOREIGN KEY (user_id) REFERENCES users (id)
    ON DELETE CASCADE
    ON UPDATE CASCADE,
  CONSTRAINT chk_credit_history CHECK (Credit_History IN (0, 1)),
  CONSTRAINT chk_prediction CHECK (prediction IN (0, 1)),
  CONSTRAINT chk_eligibility_probability CHECK (eligibility_probability BETWEEN 0 AND 1),
  CONSTRAINT chk_prediction_confidence CHECK (prediction_confidence BETWEEN 0 AND 1)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Administrator accounts are intentionally created through the CLI so
-- passwords are hashed by the application, never inserted as plain text:
--   flask --app app create-admin
