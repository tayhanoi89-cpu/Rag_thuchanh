// Buoi 14 mini Knowledge Graph constraints.
CREATE CONSTRAINT buoi14_vanban_key IF NOT EXISTS
FOR (node:VanBan) REQUIRE (node.id, node.lab_session) IS UNIQUE;

CREATE CONSTRAINT buoi14_dieukhoan_key IF NOT EXISTS
FOR (node:DieuKhoan) REQUIRE (node.id, node.lab_session) IS UNIQUE;