create database f_ass_4;
use f_ass_4;
create table student_data (
name varchar(50),
email varchar(50),
phone varchar(20),
course varchar(30),
gender varchar(6)
);
drop table student_data;
truncate table student_data;

select * from student_data;


CREATE TABLE student_data (

    name VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    phone VARCHAR(10) NOT NULL,
    dob DATE NOT NULL,
    gender VARCHAR(30) NOT NULL,
    course VARCHAR(100) NOT NULL,
    qualification VARCHAR(100) NOT NULL,
    training_mode ENUM('Online', 'Offline') NOT NULL,
    skills JSON NOT NULL,
    experience INT NOT NULL DEFAULT 0,
    address TEXT NOT NULL,
    website VARCHAR(255),
    password VARCHAR(255) NOT NULL,
    agree BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);