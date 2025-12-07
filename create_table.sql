CREATE DATABASE IF NOT EXISTS scada_db;
USE scada_db;

CREATE TABLE IF NOT EXISTS plc_data (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  timestamp DATETIME NOT NULL,
  temperature DOUBLE,
  pressure DOUBLE,
  INDEX idx_timestamp (timestamp)
);
