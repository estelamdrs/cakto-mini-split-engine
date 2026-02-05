CREATE USER IF NOT EXISTS 'senior_cakto'@'localhost' IDENTIFIED WITH mysql_native_password BY 'queroMuitoPassar';
GRANT ALL PRIVILEGES ON cakto_db.* TO 'senior_cakto'@'localhost';
FLUSH PRIVILEGES;