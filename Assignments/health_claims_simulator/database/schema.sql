-- Health Claims Simulator: database and claim-history trigger
-- Run this after the Flask application has created the claims and claim_history tables.
-- If your existing project uses a different database name, update DB_NAME in .env
-- or change the database name below to match your configuration.

CREATE DATABASE IF NOT EXISTS health_claims_simulator;
USE health_claims_simulator;

DROP TRIGGER IF EXISTS trg_claim_after_insert;
DELIMITER $$
CREATE TRIGGER trg_claim_after_insert
AFTER INSERT ON claims
FOR EACH ROW
BEGIN
    INSERT INTO claim_history (
        claim_id,
        actor_user_id,
        from_status,
        to_status,
        note,
        created_at
    )
    VALUES (
        NEW.id,
        NEW.created_by_user_id,
        NULL,
        NEW.status,
        'Claim created',
        CURRENT_TIMESTAMP
    );
END$$
DELIMITER ;
