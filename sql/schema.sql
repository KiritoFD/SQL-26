CREATE DATABASE IF NOT EXISTS moments_lab
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_general_ci;

USE moments_lab;

CREATE TABLE IF NOT EXISTS users (
  user_id INT PRIMARY KEY,
  password_hash CHAR(64) NOT NULL,
  name VARCHAR(50) NOT NULL,
  gender ENUM('男', '女', '其他') NOT NULL DEFAULT '其他',
  birth_date DATE NULL,
  age INT NULL,
  status ENUM('active', 'disabled') NOT NULL DEFAULT 'active',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT chk_users_age CHECK (age IS NULL OR age BETWEEN 0 AND 150)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS admins (
  admin_id INT PRIMARY KEY,
  password_hash CHAR(64) NOT NULL,
  name VARCHAR(50) NOT NULL,
  phone VARCHAR(30) NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS friend_groups (
  group_id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  group_name VARCHAR(50) NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT uk_friend_groups_user_name UNIQUE (user_id, group_name),
  CONSTRAINT fk_friend_groups_user
    FOREIGN KEY (user_id) REFERENCES users(user_id)
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS friendships (
  user_id INT NOT NULL,
  friend_user_id INT NOT NULL,
  group_id INT NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (user_id, friend_user_id),
  CONSTRAINT chk_friendships_not_self CHECK (user_id <> friend_user_id),
  CONSTRAINT fk_friendships_user
    FOREIGN KEY (user_id) REFERENCES users(user_id)
    ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT fk_friendships_friend
    FOREIGN KEY (friend_user_id) REFERENCES users(user_id)
    ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT fk_friendships_group
    FOREIGN KEY (group_id) REFERENCES friend_groups(group_id)
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS moments (
  moment_id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  content VARCHAR(280) NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT chk_moments_content_len CHECK (CHAR_LENGTH(content) BETWEEN 1 AND 280),
  CONSTRAINT fk_moments_user
    FOREIGN KEY (user_id) REFERENCES users(user_id)
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS comments (
  comment_id INT AUTO_INCREMENT PRIMARY KEY,
  moment_id INT NOT NULL,
  commenter_id INT NOT NULL,
  content VARCHAR(140) NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT chk_comments_content_len CHECK (CHAR_LENGTH(content) BETWEEN 1 AND 140),
  CONSTRAINT fk_comments_moment
    FOREIGN KEY (moment_id) REFERENCES moments(moment_id)
    ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT fk_comments_commenter
    FOREIGN KEY (commenter_id) REFERENCES users(user_id)
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS audit_logs (
  log_id INT AUTO_INCREMENT PRIMARY KEY,
  admin_id INT NULL,
  action_type ENUM('DELETE_MOMENT', 'DISABLE_USER') NOT NULL,
  target_user_id INT NULL,
  target_moment_id INT NULL,
  reason VARCHAR(200) NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_audit_logs_admin
    FOREIGN KEY (admin_id) REFERENCES admins(admin_id)
    ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE OR REPLACE VIEW v_admin_moments AS
SELECT
  m.moment_id,
  m.user_id AS author_id,
  m.content,
  m.created_at,
  m.updated_at,
  COUNT(c.comment_id) AS comment_count
FROM moments m
LEFT JOIN comments c ON c.moment_id = m.moment_id
GROUP BY m.moment_id, m.user_id, m.content, m.created_at, m.updated_at;

CREATE OR REPLACE VIEW v_friend_moments AS
SELECT
  f.user_id AS viewer_id,
  m.moment_id,
  m.user_id AS friend_user_id,
  m.content,
  m.created_at,
  m.updated_at,
  COUNT(c.comment_id) AS comment_count
FROM friendships f
JOIN moments m ON m.user_id = f.friend_user_id
LEFT JOIN comments c ON c.moment_id = m.moment_id
GROUP BY f.user_id, m.moment_id, m.user_id, m.content, m.created_at, m.updated_at;

DELIMITER $$

CREATE TRIGGER trg_moments_before_update
BEFORE UPDATE ON moments
FOR EACH ROW
BEGIN
  IF NEW.content <> OLD.content THEN
    SET NEW.updated_at = CURRENT_TIMESTAMP;
  END IF;
END$$

CREATE TRIGGER trg_comments_after_insert
AFTER INSERT ON comments
FOR EACH ROW
BEGIN
  UPDATE moments
  SET updated_at = CURRENT_TIMESTAMP
  WHERE moment_id = NEW.moment_id;
END$$

DELIMITER ;
