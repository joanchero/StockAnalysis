CREATE TABLE users (
    loginId  VARCHAR NOT NULL PRIMARY KEY,
    fullName VARCHAR,
    password VARCHAR
)
;

CREATE TABLE bulletins (
    id INTEGER PRIMARY KEY,
    category VARCHAR NOT NULL,
    fullText VARCHAR,
    postedBy VARCHAR NOT NULL,
    postedOn TIMESTAMP NOT NULL,
    editedBy VARCHAR NOT NULL,
    editedOn TIMESTAMP NOT NULL,
    hidden INTEGER NOT NULL
)
;

CREATE TABLE categories (
    pathName VARCHAR NOT NULL PRIMARY KEY,
    title VARCHAR,
    sortPosn INTEGER,
    sortBulletinsBy VARCHAR NOT NULL DEFAULT 'MOST_RECENTLY_EDITED',
    postingTemplate VARCHAR,
    editingTemplate VARCHAR
)

