-- SecScan AI SQL schema
-- SecScan AI PostgreSQL initialization script
-- Runs once on first container start (postgres:15-alpine) via
-- /docker-entrypoint-initdb.d. The application uses SQLAlchemy and
-- creates/migrates its own tables, so this script intentionally stays
-- minimal: it only enables extensions the ORM may rely on.

-- uuid-ossp: server-side UUID generation helpers (uuid_generate_v4, etc.)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- pgcrypto: cryptographic helpers (gen_random_uuid, digest, crypt) used for
-- hashing and random identifiers.
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
