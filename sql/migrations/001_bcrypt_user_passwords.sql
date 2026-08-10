ALTER TABLE manage_user
    MODIFY password varchar(100) CHARACTER SET utf8 COLLATE utf8_general_ci
    NOT NULL DEFAULT '' COMMENT 'BCrypt password hash.';

-- Upgrade only the repository's legacy plaintext defaults. Passwords that an
-- operator has already changed are deliberately left untouched.
UPDATE manage_user
SET password = '$2y$10$Q5C62b4cUZz0Xu5essvKf.Vo4.CSTISI/q3YT69wK3iWmpF0WwEM.'
WHERE username = 'admin' AND password = 'Yoox@123456';

UPDATE manage_user
SET password = '$2y$10$khXmgaop1Ha9DVC6Pr7il.81XKq.JsHsDvpdswAjXocufAT6JNuMG'
WHERE username = 'pilot' AND password = 'pilot123';
