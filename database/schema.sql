-- schema.sql

CREATE TABLE users (
    `id` varchar (50) NOT NULL,
    `email` varchar (50) UNIQUE NOT NULL,
    `password` varchar (50) NOT NULL,
    `admin` bool NOT NULL,
    `name` varchar (50) NOT NULL,
    `image` varchar (500) NOT NULL,
    `created_at` real NOT NULL UNIQUE,
    PRIMARY KEY (`id`)
);


CREATE INDEX idx_users_created_at ON users (`created_at`);


CREATE TABLE blogs (
    `id` varchar (50) NOT NULL UNIQUE,
    `user_id` varchar (50) NOT NULL REFERENCES users (id),
    `title` varchar (50) NOT NULL,
    `summary` varchar (200) NOT NULL,
    `content` text NOT NULL,
    `created_at` real NOT NULL UNIQUE,
    PRIMARY KEY (`id`)
);


CREATE INDEX idx_blogs_created_at ON blogs (created_at);


CREATE TABLE comments (
    `id` varchar (50) NOT NULL UNIQUE,
    `blog_id` varchar (50) NOT NULL REFERENCES blogs (`id`),
    `user_id` varchar (50) NOT NULL REFERENCES users (`id`),
    PRIMARY KEY (`id`)
);