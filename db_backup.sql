--
-- PostgreSQL database dump
--

\restrict M0IYe2XhPjm2XVrxDYLwOLxti4Gn3DMqdT7Hw8HbYO6K5eh7MqRAmnlq4IvdKyR

-- Dumped from database version 17.6
-- Dumped by pg_dump version 18.3 (Homebrew)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: _heroku; Type: SCHEMA; Schema: -; Owner: heroku_admin
--

CREATE SCHEMA _heroku;


ALTER SCHEMA _heroku OWNER TO heroku_admin;

--
-- Name: public; Type: SCHEMA; Schema: -; Owner: u2vbp82enb8hvq
--

-- *not* creating schema, since initdb creates it


ALTER SCHEMA public OWNER TO u2vbp82enb8hvq;

--
-- Name: pg_stat_statements; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pg_stat_statements WITH SCHEMA public;


--
-- Name: EXTENSION pg_stat_statements; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION pg_stat_statements IS 'track planning and execution statistics of all SQL statements executed';


--
-- Name: create_ext(); Type: FUNCTION; Schema: _heroku; Owner: heroku_admin
--

CREATE FUNCTION _heroku.create_ext() RETURNS event_trigger
    LANGUAGE plpgsql SECURITY DEFINER
    AS $$

DECLARE

  schemaname TEXT;
  databaseowner TEXT;

  r RECORD;

BEGIN
  IF tg_tag OPERATOR(pg_catalog.=) 'CREATE EXTENSION' THEN
    PERFORM _heroku.validate_search_path();

    FOR r IN SELECT * FROM pg_catalog.pg_event_trigger_ddl_commands()
    LOOP
        CONTINUE WHEN r.command_tag != 'CREATE EXTENSION' OR r.object_type != 'extension';

        schemaname := (
            SELECT n.nspname
            FROM pg_catalog.pg_extension AS e
            INNER JOIN pg_catalog.pg_namespace AS n
            ON e.extnamespace = n.oid
            WHERE e.oid = r.objid
        );

        databaseowner := (
            SELECT pg_catalog.pg_get_userbyid(d.datdba)
            FROM pg_catalog.pg_database d
            WHERE d.datname = pg_catalog.current_database()
        );
        --RAISE NOTICE 'Record for event trigger %, objid: %,tag: %, current_user: %, schema: %, database_owenr: %', r.object_identity, r.objid, tg_tag, current_user, schemaname, databaseowner;
        IF r.object_identity = 'address_standardizer_data_us' THEN
            PERFORM _heroku.grant_table_if_exists(schemaname, 'SELECT, UPDATE, INSERT, DELETE', databaseowner, 'us_gaz');
            PERFORM _heroku.grant_table_if_exists(schemaname, 'SELECT, UPDATE, INSERT, DELETE', databaseowner, 'us_lex');
            PERFORM _heroku.grant_table_if_exists(schemaname, 'SELECT, UPDATE, INSERT, DELETE', databaseowner, 'us_rules');
        ELSIF r.object_identity = 'amcheck' THEN
            -- Grant execute permissions on amcheck functions (bt_*, gin_*, and verify_*)
            PERFORM _heroku.grant_function_execute_for_extension(r.objid, schemaname, databaseowner, ARRAY['bt_%', 'gin_%', 'verify_%'], NULL);
        ELSIF r.object_identity = 'dblink' THEN
            -- Grant execute permissions on dblink functions, excluding dblink_connect_u()
            -- which allows unauthenticated connections and should remain superuser-only
            PERFORM _heroku.grant_function_execute_for_extension(r.objid, schemaname, databaseowner, ARRAY['dblink%'], 'dblink_connect_u%');
            -- Explicitly revoke permissions on dblink_connect_u functions as a safety measure
            -- in case they were granted by default or in a previous version
            BEGIN
                EXECUTE pg_catalog.format('REVOKE EXECUTE ON FUNCTION %I.dblink_connect_u(text) FROM %I;', schemaname, databaseowner);
            EXCEPTION WHEN OTHERS THEN
                -- Function might not exist, continue
                NULL;
            END;
            BEGIN
                EXECUTE pg_catalog.format('REVOKE EXECUTE ON FUNCTION %I.dblink_connect_u(text, text) FROM %I;', schemaname, databaseowner);
            EXCEPTION WHEN OTHERS THEN
                -- Function might not exist, continue
                NULL;
            END;
        ELSIF r.object_identity = 'dict_int' THEN
            EXECUTE pg_catalog.format('ALTER TEXT SEARCH DICTIONARY %I.intdict OWNER TO %I;', schemaname, databaseowner);
        ELSIF r.object_identity = 'pg_prewarm' THEN
            -- Grant execute permissions on pg_prewarm and autoprewarm functions
            PERFORM _heroku.grant_function_execute_for_extension(
                r.objid, schemaname, databaseowner, ARRAY['pg_prewarm%', 'autoprewarm%'], NULL
            );
        ELSIF r.object_identity = 'pg_partman' THEN
            PERFORM _heroku.grant_table_if_exists(schemaname, 'SELECT, UPDATE, INSERT, DELETE', databaseowner, 'part_config');
            PERFORM _heroku.grant_table_if_exists(schemaname, 'SELECT, UPDATE, INSERT, DELETE', databaseowner, 'part_config_sub');
            PERFORM _heroku.grant_table_if_exists(schemaname, 'SELECT, UPDATE, INSERT, DELETE', databaseowner, 'custom_time_partitions');
        ELSIF r.object_identity = 'pg_stat_statements' THEN
            -- Grant execute permissions on pg_stat_statements functions
            PERFORM _heroku.grant_function_execute_for_extension(
                r.objid, schemaname, databaseowner, ARRAY['pg_stat_statements%'], NULL
            );
        ELSIF r.object_identity = 'postgres_fdw' THEN
            -- Grant USAGE on the foreign data wrapper (required for creating foreign servers and user mappings)
            EXECUTE pg_catalog.format('GRANT USAGE ON FOREIGN DATA WRAPPER postgres_fdw TO %I;', databaseowner);
            -- Grant execute permissions on all postgres_fdw functions
            PERFORM _heroku.grant_function_execute_for_extension(r.objid, schemaname, databaseowner, ARRAY['postgres_fdw%'], NULL);
        ELSIF r.object_identity = 'postgis' THEN
            PERFORM _heroku.postgis_after_create();
        ELSIF r.object_identity = 'postgis_raster' THEN
            PERFORM _heroku.postgis_after_create();
            PERFORM _heroku.grant_table_if_exists(schemaname, 'SELECT', databaseowner, 'raster_columns');
            PERFORM _heroku.grant_table_if_exists(schemaname, 'SELECT', databaseowner, 'raster_overviews');
        ELSIF r.object_identity = 'postgis_topology' THEN
            PERFORM _heroku.postgis_after_create();
            EXECUTE pg_catalog.format('ALTER SCHEMA topology OWNER TO %I;', databaseowner);
            EXECUTE pg_catalog.format('GRANT USAGE ON SCHEMA topology TO %I;', databaseowner);
            EXECUTE pg_catalog.format('GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA topology TO %I;', databaseowner);
            PERFORM _heroku.grant_table_if_exists('topology', 'SELECT, UPDATE, INSERT, DELETE', databaseowner);
            EXECUTE pg_catalog.format('GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA topology TO %I;', databaseowner);
        ELSIF r.object_identity = 'postgis_tiger_geocoder' THEN
            PERFORM _heroku.postgis_after_create();
            EXECUTE pg_catalog.format('ALTER SCHEMA tiger OWNER TO %I;', databaseowner);
            EXECUTE pg_catalog.format('GRANT USAGE ON SCHEMA tiger TO %I;', databaseowner);
            EXECUTE pg_catalog.format('GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA tiger TO %I;', databaseowner);
            PERFORM _heroku.grant_table_if_exists('tiger', 'SELECT, UPDATE, INSERT, DELETE', databaseowner);
            EXECUTE pg_catalog.format('ALTER SCHEMA tiger_data OWNER TO %I;', databaseowner);
            EXECUTE pg_catalog.format('GRANT USAGE ON SCHEMA tiger_data TO %I;', databaseowner);
            EXECUTE pg_catalog.format('GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA tiger_data TO %I;', databaseowner);
            PERFORM _heroku.grant_table_if_exists('tiger_data', 'SELECT, UPDATE, INSERT, DELETE', databaseowner);
        END IF;
    END LOOP;
  END IF;
END;
$$;


ALTER FUNCTION _heroku.create_ext() OWNER TO heroku_admin;

--
-- Name: drop_ext(); Type: FUNCTION; Schema: _heroku; Owner: heroku_admin
--

CREATE FUNCTION _heroku.drop_ext() RETURNS event_trigger
    LANGUAGE plpgsql SECURITY DEFINER
    AS $$

DECLARE

  schemaname TEXT;
  databaseowner TEXT;

  r RECORD;

BEGIN
  IF tg_tag OPERATOR(pg_catalog.=) 'DROP EXTENSION' THEN
    PERFORM _heroku.validate_search_path();

    FOR r IN SELECT * FROM pg_catalog.pg_event_trigger_dropped_objects()
    LOOP
      CONTINUE WHEN r.object_type != 'extension';

      databaseowner := (
            SELECT pg_catalog.pg_get_userbyid(d.datdba)
            FROM pg_catalog.pg_database d
            WHERE d.datname = pg_catalog.current_database()
      );

      --RAISE NOTICE 'Record for event trigger %, objid: %,tag: %, current_user: %, database_owner: %, schemaname: %', r.object_identity, r.objid, tg_tag, current_user, databaseowner, r.schema_name;

      IF r.object_identity = 'postgis_topology' THEN
          EXECUTE pg_catalog.format('DROP SCHEMA IF EXISTS topology');
      END IF;
    END LOOP;

  END IF;
END;
$$;


ALTER FUNCTION _heroku.drop_ext() OWNER TO heroku_admin;

--
-- Name: extension_before_drop(); Type: FUNCTION; Schema: _heroku; Owner: heroku_admin
--

CREATE FUNCTION _heroku.extension_before_drop() RETURNS event_trigger
    LANGUAGE plpgsql SECURITY DEFINER
    AS $$

DECLARE

  query TEXT;

BEGIN
  query := (SELECT pg_catalog.current_query());

  -- RAISE NOTICE 'executing extension_before_drop: tg_event: %, tg_tag: %, current_user: %, session_user: %, query: %', tg_event, tg_tag, current_user, session_user, query;
  -- skip this validation if executed by an rds_superuser
  IF tg_tag OPERATOR(pg_catalog.=) 'DROP EXTENSION' AND NOT pg_catalog.pg_has_role(session_user, 'rds_superuser', 'MEMBER') THEN
    PERFORM _heroku.validate_search_path();

    -- DROP EXTENSION [ IF EXISTS ] name [, ...] [ CASCADE | RESTRICT ]
    IF (pg_catalog.regexp_match(query, 'DROP\s+EXTENSION\s+(IF\s+EXISTS)?.*(plpgsql)', 'i') IS NOT NULL) THEN
      RAISE EXCEPTION 'The plpgsql extension is required for database management and cannot be dropped.';
    END IF;
  END IF;
END;
$$;


ALTER FUNCTION _heroku.extension_before_drop() OWNER TO heroku_admin;

--
-- Name: grant_function_execute_for_extension(oid, text, text, text[], text); Type: FUNCTION; Schema: _heroku; Owner: heroku_admin
--

CREATE FUNCTION _heroku.grant_function_execute_for_extension(extension_oid oid, schemaname text, databaseowner text, name_patterns text[] DEFAULT NULL::text[], exclude_pattern text DEFAULT NULL::text) RETURNS void
    LANGUAGE plpgsql SECURITY DEFINER
    AS $$

DECLARE
    func_rec RECORD;

BEGIN
    PERFORM _heroku.validate_search_path();

    -- Dynamically grant execute permissions on extension functions.
    -- Finds functions belonging to the extension via pg_depend and grants execute permissions.
    FOR func_rec IN
        SELECT p.oid::regprocedure::text as func_sig
        FROM pg_catalog.pg_depend d
        JOIN pg_catalog.pg_proc p ON d.objid = p.oid
        JOIN pg_catalog.pg_namespace n ON p.pronamespace = n.oid
        WHERE d.refclassid = 'pg_catalog.pg_extension'::regclass
          AND d.refobjid = extension_oid
          AND d.deptype = 'e'
          AND n.nspname = schemaname
          AND (name_patterns IS NULL OR p.proname LIKE ANY(name_patterns))
          AND (exclude_pattern IS NULL OR p.proname NOT LIKE exclude_pattern)
    LOOP
        BEGIN
            EXECUTE pg_catalog.format('GRANT EXECUTE ON FUNCTION %s TO %I;', func_rec.func_sig, databaseowner);
        EXCEPTION WHEN OTHERS THEN
            -- Function might not exist or already granted, continue
            NULL;
        END;
    END LOOP;
END;
$$;


ALTER FUNCTION _heroku.grant_function_execute_for_extension(extension_oid oid, schemaname text, databaseowner text, name_patterns text[], exclude_pattern text) OWNER TO heroku_admin;

--
-- Name: grant_table_if_exists(text, text, text, text); Type: FUNCTION; Schema: _heroku; Owner: heroku_admin
--

CREATE FUNCTION _heroku.grant_table_if_exists(alias_schemaname text, grants text, databaseowner text, alias_tablename text DEFAULT NULL::text) RETURNS void
    LANGUAGE plpgsql SECURITY DEFINER
    AS $$

BEGIN
  PERFORM _heroku.validate_search_path();

  IF alias_tablename IS NULL THEN
    EXECUTE pg_catalog.format('GRANT %s ON ALL TABLES IN SCHEMA %I TO %I;', grants, alias_schemaname, databaseowner);
  ELSE
    IF EXISTS (SELECT 1 FROM pg_catalog.pg_tables WHERE pg_tables.schemaname = alias_schemaname AND pg_tables.tablename = alias_tablename) THEN
      EXECUTE pg_catalog.format('GRANT %s ON TABLE %I.%I TO %I;', grants, alias_schemaname, alias_tablename, databaseowner);
    END IF;
  END IF;
END;
$$;


ALTER FUNCTION _heroku.grant_table_if_exists(alias_schemaname text, grants text, databaseowner text, alias_tablename text) OWNER TO heroku_admin;

--
-- Name: postgis_after_create(); Type: FUNCTION; Schema: _heroku; Owner: heroku_admin
--

CREATE FUNCTION _heroku.postgis_after_create() RETURNS void
    LANGUAGE plpgsql SECURITY DEFINER
    AS $$
DECLARE
    schemaname TEXT;
    databaseowner TEXT;
BEGIN
    PERFORM _heroku.validate_search_path();

    schemaname := (
        SELECT n.nspname
        FROM pg_catalog.pg_extension AS e
        INNER JOIN pg_catalog.pg_namespace AS n ON e.extnamespace = n.oid
        WHERE e.extname = 'postgis'
    );
    databaseowner := (
        SELECT pg_catalog.pg_get_userbyid(d.datdba)
        FROM pg_catalog.pg_database d
        WHERE d.datname = pg_catalog.current_database()
    );

    EXECUTE pg_catalog.format('GRANT EXECUTE ON FUNCTION %I.st_tileenvelope TO %I;', schemaname, databaseowner);
    EXECUTE pg_catalog.format('GRANT SELECT, UPDATE, INSERT, DELETE ON TABLE %I.spatial_ref_sys TO %I;', schemaname, databaseowner);
END;
$$;


ALTER FUNCTION _heroku.postgis_after_create() OWNER TO heroku_admin;

--
-- Name: sanitize_search_path(text); Type: FUNCTION; Schema: _heroku; Owner: heroku_admin
--

CREATE FUNCTION _heroku.sanitize_search_path(unsafe_search_path text DEFAULT NULL::text) RETURNS text
    LANGUAGE plpgsql
    AS $$
DECLARE
  search_path_parts TEXT[];
  safe_search_path TEXT;
BEGIN
  IF unsafe_search_path IS NULL THEN
    unsafe_search_path := pg_catalog.current_setting('search_path');
  END IF;

  search_path_parts := pg_catalog.string_to_array(unsafe_search_path, ',');
  search_path_parts := (
    SELECT pg_catalog.array_agg(TRIM(schema_name::text))
    FROM pg_catalog.unnest(search_path_parts) AS schema_name
    WHERE TRIM(schema_name::text) OPERATOR(pg_catalog.!~~) 'pg_temp%'
  );
  search_path_parts := (SELECT pg_catalog.array_remove(search_path_parts, 'pg_catalog'));
  search_path_parts := (SELECT pg_catalog.array_append(search_path_parts, 'pg_temp'));
  SELECT pg_catalog.array_to_string(search_path_parts, ',') INTO safe_search_path;
  RETURN safe_search_path;
END;
$$;


ALTER FUNCTION _heroku.sanitize_search_path(unsafe_search_path text) OWNER TO heroku_admin;

--
-- Name: validate_extension(); Type: FUNCTION; Schema: _heroku; Owner: heroku_admin
--

CREATE FUNCTION _heroku.validate_extension() RETURNS event_trigger
    LANGUAGE plpgsql SECURITY DEFINER
    AS $$

DECLARE

  schemaname TEXT;
  r RECORD;

BEGIN
  IF tg_tag OPERATOR(pg_catalog.=) 'CREATE EXTENSION' THEN
    PERFORM _heroku.validate_search_path();

    FOR r IN SELECT * FROM pg_catalog.pg_event_trigger_ddl_commands()
    LOOP
      CONTINUE WHEN r.command_tag != 'CREATE EXTENSION' OR r.object_type != 'extension';

      schemaname := (
        SELECT n.nspname
        FROM pg_catalog.pg_extension AS e
        INNER JOIN pg_catalog.pg_namespace AS n
        ON e.extnamespace = n.oid
        WHERE e.oid = r.objid
      );

      IF schemaname = '_heroku' THEN
        RAISE EXCEPTION 'Creating extensions in the _heroku schema is not allowed';
      END IF;
    END LOOP;
  END IF;
END;
$$;


ALTER FUNCTION _heroku.validate_extension() OWNER TO heroku_admin;

--
-- Name: validate_search_path(); Type: FUNCTION; Schema: _heroku; Owner: heroku_admin
--

CREATE FUNCTION _heroku.validate_search_path() RETURNS void
    LANGUAGE plpgsql SECURITY DEFINER
    AS $$
DECLARE

  current_search_path TEXT;
  safe_search_path TEXT;
  current_schemas TEXT[];
  pg_catalog_index INTEGER;

BEGIN

  current_search_path := pg_catalog.current_setting('search_path');
  current_schemas := (SELECT pg_catalog.current_schemas(true));
  safe_search_path := _heroku.sanitize_search_path(current_search_path);

  IF current_schemas[1] OPERATOR(pg_catalog.~~) 'pg_temp%' THEN
    RAISE EXCEPTION 'Unable to perform this operation with current schema configuration. Try: SET search_path TO %.', safe_search_path;
  END IF;

  IF ('pg_catalog' OPERATOR(pg_catalog.=) ANY(current_schemas)) THEN
    SELECT pg_catalog.array_position(current_schemas, 'pg_catalog') INTO pg_catalog_index;
    IF pg_catalog_index OPERATOR(pg_catalog.!=) 1 THEN
      RAISE EXCEPTION 'Unable to perform this operation with current schema configuration. Try: SET search_path TO %.', safe_search_path;
    END IF;
  END IF;
END;
$$;


ALTER FUNCTION _heroku.validate_search_path() OWNER TO heroku_admin;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: auth_group; Type: TABLE; Schema: public; Owner: u2vbp82enb8hvq
--

CREATE TABLE public.auth_group (
    id integer NOT NULL,
    name character varying(150) NOT NULL
);


ALTER TABLE public.auth_group OWNER TO u2vbp82enb8hvq;

--
-- Name: auth_group_id_seq; Type: SEQUENCE; Schema: public; Owner: u2vbp82enb8hvq
--

ALTER TABLE public.auth_group ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.auth_group_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: auth_group_permissions; Type: TABLE; Schema: public; Owner: u2vbp82enb8hvq
--

CREATE TABLE public.auth_group_permissions (
    id bigint NOT NULL,
    group_id integer NOT NULL,
    permission_id integer NOT NULL
);


ALTER TABLE public.auth_group_permissions OWNER TO u2vbp82enb8hvq;

--
-- Name: auth_group_permissions_id_seq; Type: SEQUENCE; Schema: public; Owner: u2vbp82enb8hvq
--

ALTER TABLE public.auth_group_permissions ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.auth_group_permissions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: auth_permission; Type: TABLE; Schema: public; Owner: u2vbp82enb8hvq
--

CREATE TABLE public.auth_permission (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    content_type_id integer NOT NULL,
    codename character varying(100) NOT NULL
);


ALTER TABLE public.auth_permission OWNER TO u2vbp82enb8hvq;

--
-- Name: auth_permission_id_seq; Type: SEQUENCE; Schema: public; Owner: u2vbp82enb8hvq
--

ALTER TABLE public.auth_permission ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.auth_permission_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: auth_user; Type: TABLE; Schema: public; Owner: u2vbp82enb8hvq
--

CREATE TABLE public.auth_user (
    id integer NOT NULL,
    password character varying(128) NOT NULL,
    last_login timestamp with time zone,
    is_superuser boolean NOT NULL,
    username character varying(150) NOT NULL,
    first_name character varying(150) NOT NULL,
    last_name character varying(150) NOT NULL,
    email character varying(254) NOT NULL,
    is_staff boolean NOT NULL,
    is_active boolean NOT NULL,
    date_joined timestamp with time zone NOT NULL
);


ALTER TABLE public.auth_user OWNER TO u2vbp82enb8hvq;

--
-- Name: auth_user_groups; Type: TABLE; Schema: public; Owner: u2vbp82enb8hvq
--

CREATE TABLE public.auth_user_groups (
    id bigint NOT NULL,
    user_id integer NOT NULL,
    group_id integer NOT NULL
);


ALTER TABLE public.auth_user_groups OWNER TO u2vbp82enb8hvq;

--
-- Name: auth_user_groups_id_seq; Type: SEQUENCE; Schema: public; Owner: u2vbp82enb8hvq
--

ALTER TABLE public.auth_user_groups ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.auth_user_groups_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: auth_user_id_seq; Type: SEQUENCE; Schema: public; Owner: u2vbp82enb8hvq
--

ALTER TABLE public.auth_user ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.auth_user_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: auth_user_user_permissions; Type: TABLE; Schema: public; Owner: u2vbp82enb8hvq
--

CREATE TABLE public.auth_user_user_permissions (
    id bigint NOT NULL,
    user_id integer NOT NULL,
    permission_id integer NOT NULL
);


ALTER TABLE public.auth_user_user_permissions OWNER TO u2vbp82enb8hvq;

--
-- Name: auth_user_user_permissions_id_seq; Type: SEQUENCE; Schema: public; Owner: u2vbp82enb8hvq
--

ALTER TABLE public.auth_user_user_permissions ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.auth_user_user_permissions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: core_agent; Type: TABLE; Schema: public; Owner: u2vbp82enb8hvq
--

CREATE TABLE public.core_agent (
    id bigint NOT NULL,
    name character varying(120) NOT NULL,
    title character varying(120) NOT NULL,
    email character varying(254) NOT NULL,
    phone character varying(50) NOT NULL,
    photo character varying(2000),
    bio text NOT NULL,
    active boolean NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    user_id integer
);


ALTER TABLE public.core_agent OWNER TO u2vbp82enb8hvq;

--
-- Name: core_agent_id_seq; Type: SEQUENCE; Schema: public; Owner: u2vbp82enb8hvq
--

ALTER TABLE public.core_agent ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.core_agent_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: core_agent_properties; Type: TABLE; Schema: public; Owner: u2vbp82enb8hvq
--

CREATE TABLE public.core_agent_properties (
    id bigint NOT NULL,
    agent_id bigint NOT NULL,
    property_id bigint NOT NULL
);


ALTER TABLE public.core_agent_properties OWNER TO u2vbp82enb8hvq;

--
-- Name: core_agent_properties_id_seq; Type: SEQUENCE; Schema: public; Owner: u2vbp82enb8hvq
--

ALTER TABLE public.core_agent_properties ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.core_agent_properties_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: core_bookingrequest; Type: TABLE; Schema: public; Owner: u2vbp82enb8hvq
--

CREATE TABLE public.core_bookingrequest (
    id bigint NOT NULL,
    name character varying(120) NOT NULL,
    email character varying(254) NOT NULL,
    requested_date date NOT NULL,
    message text NOT NULL,
    created_at timestamp with time zone NOT NULL,
    property_id bigint NOT NULL
);


ALTER TABLE public.core_bookingrequest OWNER TO u2vbp82enb8hvq;

--
-- Name: core_bookingrequest_id_seq; Type: SEQUENCE; Schema: public; Owner: u2vbp82enb8hvq
--

ALTER TABLE public.core_bookingrequest ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.core_bookingrequest_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: core_contactmessage; Type: TABLE; Schema: public; Owner: u2vbp82enb8hvq
--

CREATE TABLE public.core_contactmessage (
    id bigint NOT NULL,
    name character varying(120) NOT NULL,
    email character varying(254) NOT NULL,
    message text NOT NULL,
    created_at timestamp with time zone NOT NULL
);


ALTER TABLE public.core_contactmessage OWNER TO u2vbp82enb8hvq;

--
-- Name: core_contactmessage_id_seq; Type: SEQUENCE; Schema: public; Owner: u2vbp82enb8hvq
--

ALTER TABLE public.core_contactmessage ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.core_contactmessage_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: core_municipality; Type: TABLE; Schema: public; Owner: u2vbp82enb8hvq
--

CREATE TABLE public.core_municipality (
    id bigint NOT NULL,
    name character varying(120) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    description text NOT NULL
);


ALTER TABLE public.core_municipality OWNER TO u2vbp82enb8hvq;

--
-- Name: core_municipality_id_seq; Type: SEQUENCE; Schema: public; Owner: u2vbp82enb8hvq
--

ALTER TABLE public.core_municipality ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.core_municipality_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: core_municipality_properties; Type: TABLE; Schema: public; Owner: u2vbp82enb8hvq
--

CREATE TABLE public.core_municipality_properties (
    id bigint NOT NULL,
    municipality_id bigint NOT NULL,
    property_id bigint NOT NULL
);


ALTER TABLE public.core_municipality_properties OWNER TO u2vbp82enb8hvq;

--
-- Name: core_municipality_properties_id_seq; Type: SEQUENCE; Schema: public; Owner: u2vbp82enb8hvq
--

ALTER TABLE public.core_municipality_properties ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.core_municipality_properties_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: core_note; Type: TABLE; Schema: public; Owner: u2vbp82enb8hvq
--

CREATE TABLE public.core_note (
    id bigint NOT NULL,
    text character varying(200) NOT NULL,
    done boolean NOT NULL,
    created_at timestamp with time zone NOT NULL
);


ALTER TABLE public.core_note OWNER TO u2vbp82enb8hvq;

--
-- Name: core_note_id_seq; Type: SEQUENCE; Schema: public; Owner: u2vbp82enb8hvq
--

ALTER TABLE public.core_note ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.core_note_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: core_property; Type: TABLE; Schema: public; Owner: u2vbp82enb8hvq
--

CREATE TABLE public.core_property (
    id bigint NOT NULL,
    title character varying(120) NOT NULL,
    address character varying(255) NOT NULL,
    price numeric(12,2),
    status character varying(20) NOT NULL,
    description text NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    created_by_id integer,
    municipality_id bigint,
    is_featured boolean NOT NULL
);


ALTER TABLE public.core_property OWNER TO u2vbp82enb8hvq;

--
-- Name: core_property_id_seq; Type: SEQUENCE; Schema: public; Owner: u2vbp82enb8hvq
--

ALTER TABLE public.core_property ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.core_property_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: core_propertyimage; Type: TABLE; Schema: public; Owner: u2vbp82enb8hvq
--

CREATE TABLE public.core_propertyimage (
    id bigint NOT NULL,
    image character varying(2000) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    property_id bigint NOT NULL
);


ALTER TABLE public.core_propertyimage OWNER TO u2vbp82enb8hvq;

--
-- Name: core_propertyimage_id_seq; Type: SEQUENCE; Schema: public; Owner: u2vbp82enb8hvq
--

ALTER TABLE public.core_propertyimage ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.core_propertyimage_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: core_service; Type: TABLE; Schema: public; Owner: u2vbp82enb8hvq
--

CREATE TABLE public.core_service (
    id bigint NOT NULL,
    name character varying(120) NOT NULL,
    description text NOT NULL,
    active boolean NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    image character varying(2000)
);


ALTER TABLE public.core_service OWNER TO u2vbp82enb8hvq;

--
-- Name: core_service_id_seq; Type: SEQUENCE; Schema: public; Owner: u2vbp82enb8hvq
--

ALTER TABLE public.core_service ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.core_service_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: core_serviceimage; Type: TABLE; Schema: public; Owner: u2vbp82enb8hvq
--

CREATE TABLE public.core_serviceimage (
    id bigint NOT NULL,
    image character varying(2000) NOT NULL,
    created_at timestamp with time zone NOT NULL,
    service_id bigint NOT NULL
);


ALTER TABLE public.core_serviceimage OWNER TO u2vbp82enb8hvq;

--
-- Name: core_serviceimage_id_seq; Type: SEQUENCE; Schema: public; Owner: u2vbp82enb8hvq
--

ALTER TABLE public.core_serviceimage ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.core_serviceimage_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: django_admin_log; Type: TABLE; Schema: public; Owner: u2vbp82enb8hvq
--

CREATE TABLE public.django_admin_log (
    id integer NOT NULL,
    action_time timestamp with time zone NOT NULL,
    object_id text,
    object_repr character varying(200) NOT NULL,
    action_flag smallint NOT NULL,
    change_message text NOT NULL,
    content_type_id integer,
    user_id integer NOT NULL,
    CONSTRAINT django_admin_log_action_flag_check CHECK ((action_flag >= 0))
);


ALTER TABLE public.django_admin_log OWNER TO u2vbp82enb8hvq;

--
-- Name: django_admin_log_id_seq; Type: SEQUENCE; Schema: public; Owner: u2vbp82enb8hvq
--

ALTER TABLE public.django_admin_log ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.django_admin_log_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: django_content_type; Type: TABLE; Schema: public; Owner: u2vbp82enb8hvq
--

CREATE TABLE public.django_content_type (
    id integer NOT NULL,
    app_label character varying(100) NOT NULL,
    model character varying(100) NOT NULL
);


ALTER TABLE public.django_content_type OWNER TO u2vbp82enb8hvq;

--
-- Name: django_content_type_id_seq; Type: SEQUENCE; Schema: public; Owner: u2vbp82enb8hvq
--

ALTER TABLE public.django_content_type ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.django_content_type_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: django_migrations; Type: TABLE; Schema: public; Owner: u2vbp82enb8hvq
--

CREATE TABLE public.django_migrations (
    id bigint NOT NULL,
    app character varying(255) NOT NULL,
    name character varying(255) NOT NULL,
    applied timestamp with time zone NOT NULL
);


ALTER TABLE public.django_migrations OWNER TO u2vbp82enb8hvq;

--
-- Name: django_migrations_id_seq; Type: SEQUENCE; Schema: public; Owner: u2vbp82enb8hvq
--

ALTER TABLE public.django_migrations ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME public.django_migrations_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: django_session; Type: TABLE; Schema: public; Owner: u2vbp82enb8hvq
--

CREATE TABLE public.django_session (
    session_key character varying(40) NOT NULL,
    session_data text NOT NULL,
    expire_date timestamp with time zone NOT NULL
);


ALTER TABLE public.django_session OWNER TO u2vbp82enb8hvq;

--
-- Data for Name: auth_group; Type: TABLE DATA; Schema: public; Owner: u2vbp82enb8hvq
--

COPY public.auth_group (id, name) FROM stdin;
1	Agents
\.


--
-- Data for Name: auth_group_permissions; Type: TABLE DATA; Schema: public; Owner: u2vbp82enb8hvq
--

COPY public.auth_group_permissions (id, group_id, permission_id) FROM stdin;
\.


--
-- Data for Name: auth_permission; Type: TABLE DATA; Schema: public; Owner: u2vbp82enb8hvq
--

COPY public.auth_permission (id, name, content_type_id, codename) FROM stdin;
1	Can add log entry	1	add_logentry
2	Can change log entry	1	change_logentry
3	Can delete log entry	1	delete_logentry
4	Can view log entry	1	view_logentry
5	Can add permission	3	add_permission
6	Can change permission	3	change_permission
7	Can delete permission	3	delete_permission
8	Can view permission	3	view_permission
9	Can add group	2	add_group
10	Can change group	2	change_group
11	Can delete group	2	delete_group
12	Can view group	2	view_group
13	Can add user	4	add_user
14	Can change user	4	change_user
15	Can delete user	4	delete_user
16	Can view user	4	view_user
17	Can add content type	5	add_contenttype
18	Can change content type	5	change_contenttype
19	Can delete content type	5	delete_contenttype
20	Can view content type	5	view_contenttype
21	Can add session	6	add_session
22	Can change session	6	change_session
23	Can delete session	6	delete_session
24	Can view session	6	view_session
25	Can add note	11	add_note
26	Can change note	11	change_note
27	Can delete note	11	delete_note
28	Can view note	11	view_note
29	Can add property	12	add_property
30	Can change property	12	change_property
31	Can delete property	12	delete_property
32	Can view property	12	view_property
33	Can add property image	13	add_propertyimage
34	Can change property image	13	change_propertyimage
35	Can delete property image	13	delete_propertyimage
36	Can view property image	13	view_propertyimage
37	Can add contact message	9	add_contactmessage
38	Can change contact message	9	change_contactmessage
39	Can delete contact message	9	delete_contactmessage
40	Can view contact message	9	view_contactmessage
41	Can add agent	7	add_agent
42	Can change agent	7	change_agent
43	Can delete agent	7	delete_agent
44	Can view agent	7	view_agent
45	Can add municipality	10	add_municipality
46	Can change municipality	10	change_municipality
47	Can delete municipality	10	delete_municipality
48	Can view municipality	10	view_municipality
49	Can add service	14	add_service
50	Can change service	14	change_service
51	Can delete service	14	delete_service
52	Can view service	14	view_service
53	Can add booking request	8	add_bookingrequest
54	Can change booking request	8	change_bookingrequest
55	Can delete booking request	8	delete_bookingrequest
56	Can view booking request	8	view_bookingrequest
57	Can add service image	15	add_serviceimage
58	Can change service image	15	change_serviceimage
59	Can delete service image	15	delete_serviceimage
60	Can view service image	15	view_serviceimage
\.


--
-- Data for Name: auth_user; Type: TABLE DATA; Schema: public; Owner: u2vbp82enb8hvq
--

COPY public.auth_user (id, password, last_login, is_superuser, username, first_name, last_name, email, is_staff, is_active, date_joined) FROM stdin;
1	pbkdf2_sha256$1200000$QhvjlzinSd9KA54SqKWjIk$fmMhOLCqHWgndIvU0Q03X4z2wIK0yz/oHmHsPHTEDLw=	2026-03-25 06:41:15.488952+00	t	damc			damc@l.com	t	t	2026-03-24 11:09:35.631334+00
9	pbkdf2_sha256$1200000$QPARrey6HVIZKfeEIKcuz9$02Vi7BcXKDwUdwXwnkw2GHm6eFkNDpQCnT8AeIztL8M=	2026-03-25 10:27:37.443317+00	t	damcfrealtyinc@gmail.com			damcfrealtyinc@gmail.com	t	t	2026-03-25 01:32:50+00
\.


--
-- Data for Name: auth_user_groups; Type: TABLE DATA; Schema: public; Owner: u2vbp82enb8hvq
--

COPY public.auth_user_groups (id, user_id, group_id) FROM stdin;
14	9	1
\.


--
-- Data for Name: auth_user_user_permissions; Type: TABLE DATA; Schema: public; Owner: u2vbp82enb8hvq
--

COPY public.auth_user_user_permissions (id, user_id, permission_id) FROM stdin;
\.


--
-- Data for Name: core_agent; Type: TABLE DATA; Schema: public; Owner: u2vbp82enb8hvq
--

COPY public.core_agent (id, name, title, email, phone, photo, bio, active, created_at, updated_at, user_id) FROM stdin;
14	Rosely Dagsa	Licensed Real Estate Broker & Appraiser	damcfrealtyinc@gmail.com	+639300157769	https://res.cloudinary.com/dzsiogux5/image/upload/v1/media/agents/AoCQ8zpUcJs-632823110_26185503014417155_5513034604889649906_n_mb9vtx	Rosely C. Dagsa is a newly licensed Real Estate Broker who successfully passed the April 2025 Real Estate Broker Licensure Examination (REBLE). With a strong passion for helping clients make smart property decisions, she specializes in residential and investment properties, with a growing focus on opportunities in areas like Siargao Island.\r\nDedicated to ethical practice and client-centered service, Rosely emphasizes due diligence—such as verifying developer compliance with the Balanced Housing Law—and building long-term relationships. In 2025, she achieved a remarkable milestone by selling 101 units, earning recognition as a top sales performer.\r\nShe is also a licensed Real Estate Appraiser, an aspiring MBA holder, content creator, and NLP/soft skills trainer. Known for her perseverance, faith-driven approach, and commitment to excellence, Rosely is ready to guide buyers, sellers, and investors with professionalism and integrity.\r\n\r\nAreas of Focus: Siargao Island investments and nationwide real estate opportunities.	t	2026-03-25 01:33:06.574807+00	2026-03-25 01:33:06.574839+00	9
\.


--
-- Data for Name: core_agent_properties; Type: TABLE DATA; Schema: public; Owner: u2vbp82enb8hvq
--

COPY public.core_agent_properties (id, agent_id, property_id) FROM stdin;
1	14	34
2	14	35
3	14	36
4	14	37
5	14	38
\.


--
-- Data for Name: core_bookingrequest; Type: TABLE DATA; Schema: public; Owner: u2vbp82enb8hvq
--

COPY public.core_bookingrequest (id, name, email, requested_date, message, created_at, property_id) FROM stdin;
\.


--
-- Data for Name: core_contactmessage; Type: TABLE DATA; Schema: public; Owner: u2vbp82enb8hvq
--

COPY public.core_contactmessage (id, name, email, message, created_at) FROM stdin;
1	digital word	myworldisadigitallife@gmail.com	Booking request: lot1\r\nProperty link: http://127.0.0.1:8000/listings/1/\r\n\r\n\r\n\r\nInquiry: lot1\r\n\r\nRequested date: 2026-03-24\r\n\r\nContact me:\r\ndigital word\r\nmyworldisadigitallife@gmail.com	2026-03-24 11:30:50.020968+00
2	mynae	myworldisadigitallife@gmail.com	Booking request: lot1\r\nProperty link: http://127.0.0.1:8000/listings/1/\r\n\r\nInquiry: lot1\r\n\r\nRequested date: 2026-03-24\r\n\r\nContact me:\r\nmynae\r\nmyworldisadigitallife@gmail.com\r\nPhone/WhatsApp: 1	2026-03-24 11:30:59.36891+00
3	myna	dd@l.com	Booking request: title1\r\nProperty link: http://127.0.0.1:8000/listings/6/\r\n\r\n\r\n\r\nInquiry: title1\r\n\r\nRequested date: 2026-03-24\r\n\r\nContact me:\r\nmyna\r\ndd@l.com\r\nPhone/WhatsApp: 2	2026-03-24 12:17:35.311958+00
4	test2	emailtest@l.com	Booking request: title1\nProperty link: https://www.damcfrealty-and-businessconsultancy.com/listings/6/	2026-03-24 12:40:54.666442+00
5	test2	emailtest@l.com	Booking request: title1\r\nProperty link: https://www.damcfrealty-and-businessconsultancy.com/listings/6/\r\n\r\n\r\n\r\nInquiry: title1\r\n\r\nRequested date: 2026-03-25\r\n\r\nContact me:\r\ntest2\r\nemailtest@l.com\r\nPhone/WhatsApp: 002	2026-03-24 12:40:54.731507+00
6	mynametest	l1@l.com	test\r\n\r\nInquiry: subs\r\n\r\nRequested date: 2026-03-24\r\n\r\nContact me:\r\nmynametest\r\nl1@l.com\r\nPhone/WhatsApp: asd	2026-03-24 12:48:51.109822+00
7	direct book	gg@l.com	Booking request: title1\nProperty link: http://127.0.0.1:8000/listings/6/	2026-03-24 12:57:07.495432+00
8	direct book	gg@l.com	Booking request: title1\r\nProperty link: http://127.0.0.1:8000/listings/6/\r\n\r\n\r\n\r\nInquiry: title1\r\n\r\nRequested date: 2026-03-24\r\n\r\nContact me:\r\ndirect book\r\ngg@l.com	2026-03-24 12:57:09.259543+00
\.


--
-- Data for Name: core_municipality; Type: TABLE DATA; Schema: public; Owner: u2vbp82enb8hvq
--

COPY public.core_municipality (id, name, created_at, updated_at, description) FROM stdin;
34	Burgos	2026-03-25 10:29:04.587543+00	2026-03-25 10:29:04.587553+00	
35	Dapa	2026-03-25 10:29:22.118175+00	2026-03-25 10:29:22.118185+00	
36	Del Carmen	2026-03-25 10:29:38.144702+00	2026-03-25 10:29:38.144713+00	
37	General Luna	2026-03-25 10:29:54.576305+00	2026-03-25 10:29:54.576314+00	
38	Pilar	2026-03-25 10:30:21.681937+00	2026-03-25 10:30:21.681948+00	
39	San Benito	2026-03-25 10:30:39.151559+00	2026-03-25 10:30:39.151569+00	
40	San Isidro	2026-03-25 10:30:54.677429+00	2026-03-25 10:30:54.67744+00	
41	Santa Monica	2026-03-25 10:31:09.519653+00	2026-03-25 10:31:09.519663+00	
42	Socorro	2026-03-25 10:31:21.80064+00	2026-03-25 10:31:21.800651+00	
\.


--
-- Data for Name: core_municipality_properties; Type: TABLE DATA; Schema: public; Owner: u2vbp82enb8hvq
--

COPY public.core_municipality_properties (id, municipality_id, property_id) FROM stdin;
34	37	34
35	42	35
36	35	36
37	35	37
38	35	38
\.


--
-- Data for Name: core_note; Type: TABLE DATA; Schema: public; Owner: u2vbp82enb8hvq
--

COPY public.core_note (id, text, done, created_at) FROM stdin;
\.


--
-- Data for Name: core_property; Type: TABLE DATA; Schema: public; Owner: u2vbp82enb8hvq
--

COPY public.core_property (id, title, address, price, status, description, created_at, updated_at, created_by_id, municipality_id, is_featured) FROM stdin;
34	High way	Siargao	0.00	for_sale	Ever dreamed of waking up to the sound of the Pacific and the scent of saltwater? We are offering a rare opportunity to own a slice of the Siargao lifestyle. Whether you’re looking to build your dream surf villa or a boutique eco-resort, this prime lot in  General Luna Siargao puts you right at the heart of the island’s magic. Secure your spot in the Surfing Capital before the secret is completely out!\r\n\r\n🌿Rare small cut (238 sqm.) of flat land in General Luna\r\n🌿Rare balance of privacy and prime location\r\n🌿5-minute walk to a quiet beach\r\n🌿Walking distance to Ocean 9 and prime surf spots\r\n🌿Peaceful setting (hear ocean waves from the distance)\r\n🌿2nd lot from concrete barangay road (added privacy; ease of driving even during rainy season)\r\n🌿6-meter wide access road towards the land\r\n🌿Corner lot with dual access (front and right side)\r\n🌿In a growing luxury Airbnb neighborhood\r\n🌿Perfect for your dream home or a high-end rental investment.\r\n\r\n📜 Clean title under a sole owner (simpler paperwork, faster transactions)\r\n\r\nSend a message to inquire.\r\n\r\n#RoselyDagsa\r\n#LicensedBroker\r\n#LicensedAppraiser\r\n#SurigaoProperty\r\n#HighwayProperty\r\n#RealEstatePhilippines\r\n#InvestmentOpportunity\r\n#LandForSale\r\n#PrimeLocation\r\n#SmartInvesting	2026-03-25 10:33:25.871163+00	2026-03-25 10:33:25.871174+00	9	37	f
35	Prime investment	Barangay Socorro, Surigao del Norte Siargao Island!	0.00	for_sale	📍 Prime Investment Opportunity in Barangay Socorro, Surigao del Norte Siargao Island!\r\nLooking for your next big move? This 10,70 lot is perfectly positioned in the heart of Pamosaingan Bucas Grande Island. \r\n\r\nSize: 10,570 sqm\r\n\r\nZoning: [Residential/Commercial/Agricultural]\r\n\r\nKey Feature: Just 3 minutes from beach and 10 minutes to waterfalls.\r\n\r\nReady for: [Building a villa/Commercial space/Farming]\r\n\r\nDon't wait for the prices to peak—secure your piece of paradise now.\r\n\r\nCall to Action: DM for the price and exact location. Let’s get you a viewing!\r\n\r\n#RoselyDagsa\r\n#LicensedBroker\r\n#LicensedAppraiser\r\n#SurigaoProperty\r\n#HighwayProperty\r\n#RealEstatePhilippines\r\n#InvestmentOpportunity\r\n#LandForSale\r\n#PrimeLocation\r\n#SmartInvesting	2026-03-25 10:35:41.564856+00	2026-03-25 10:35:41.564865+00	9	42	f
36	PRIME HIGHWAY	Surigao City	0.00	for_sale	PROPERTY FOR SALE – SURIGAO CITY \r\n\r\nOpportunity doesn’t come twice — especially when it’s along the highway.\r\n\r\nLocation: Sitio Bioborjan, Brgy. Rizal, Surigao City\r\n Lot Area: 1,200 SQM\r\nFrontage: Along National Highway (high visibility & accessibility)\r\n\r\n Ideal for:\r\n Commercial development (gas station, warehouse, retail)\r\n Mixed-use investment\r\nLong-term land banking in a growing area\r\n\r\n Price:\r\n₱4,000/sqm (Negotiable)\r\n Owner is open to ₱3,500/sqm NET\r\n\r\n Why invest here?\r\nStrategic highway location = strong appreciation potential + business-ready positioning.\r\n\r\nAs a Licensed Broker & Appraiser, I ensure:\r\n Verified documents\r\n Proper valuation guidance\r\nSmooth and secure transaction\r\n\r\n Serious buyers & investors — message me for site viewing and details.\r\n\r\n#RoselyDagsa\r\n#LicensedBroker\r\n#LicensedAppraiser\r\n#SurigaoProperty\r\n#HighwayProperty\r\n#RealEstatePhilippines\r\n#InvestmentOpportunity\r\n#LandForSale\r\n#PrimeLocation\r\n#SmartInvesting	2026-03-25 10:36:50.241514+00	2026-03-25 10:36:50.241528+00	9	35	f
37	BEACHFRONT PROPERTY	Brgy. San Carlos, Dapa — near Jubang International Port	15000000.00	for_sale	📋 Beach front RUSH BEACHFRONT PROPERTY FOR SALE — 1 HECTARE! 🌊\r\n🏡 NEW LISTING\r\n━━━━━━━━━━━━━━━━\r\n\r\n💰 PRICE: ₱15,000,000\r\n\r\n📍 LOCATION: Dapa\r\n📫 Brgy. San Carlos, Dapa — near Jubang International Port\r\n\r\n✨ STATUS: For sale\r\n\r\n📝 INFORMATION:\r\nA rare chance to own a stunning stretch of beachfront overlooking the Dapa Channel — peaceful, private, and full of potential. Perfect for resort development, vacation homes, wellness retreat, or investment holding.\r\n📍 Location: Brgy. San Carlos, Dapa — near Jubang International Port\r\n📏 Total Area: 1 Hectare\r\n💰 Price: ₱15,000,000 — Negotiable\r\n📑 Due diligence ready\r\nEnjoy wide sandy beachfront, coconut trees, clear waters, and beautiful island views — a true tropical gem waiting for the right...\r\n\r\n━━━━━━━━━━━━━━━━\r\n💬 Contact us for viewing schedule!\r\n📞 +639300157769\r\n📧 damcfrealtyinc@gmail.com\r\n\r\n🔗 View full details: https://www.damcfrealty-and-businessconsultancy.com/listings/14/\r\n\r\n#DAMCFRealty #RealEstate #Siargao #PropertyListing\r\n#PropertyForSale #HouseAndLot	2026-03-25 10:39:07.838878+00	2026-03-25 10:39:07.838888+00	9	35	f
38	Just 6 minutes from the famous surfing	Union Road, Don Paulino (Guiwan), Dapa, Siargao	700000.00	for_sale	Own a Slice of Paradise in Siargao! \r\nJust 6 minutes from the famous surfing spots via Union Road — peaceful, green, and ideal for your dream project.\r\n Location: Union Road, Don Paulino (Guiwan), Dapa, Siargao\r\n Price: ₱700,000 only\r\n Lot Area: 100 sqm\r\n Title Status: Clean & Ready for Transfer\r\n Why You’ll Love This Property:\r\n Peaceful coconut-lined surroundings\r\n Accessible location near Tourism Road\r\n Ideal for a vacation house, retreat space, rental unit, or long-term investment\r\n Flat and usable land — easy to develop\r\nWhether you’re building a personal hideaway or an income-generating property, this is a rare and affordable opportunity in Siargao \r\n Want to see it in person?\r\nMessage us your preferred schedule — we’re happy to assist you with a site viewing 😊\r\n📞 Contact: WhatsApp 63930-015-7769\r\ndamcfrealtyinc@gmail.com\r\n👩‍💼 Rosely C. Dagsa, REB | REA	2026-03-25 10:41:45.467404+00	2026-03-25 10:41:45.467416+00	9	35	f
\.


--
-- Data for Name: core_propertyimage; Type: TABLE DATA; Schema: public; Owner: u2vbp82enb8hvq
--

COPY public.core_propertyimage (id, image, created_at, property_id) FROM stdin;
34	https://res.cloudinary.com/dhqsdzxkn/image/upload/v1/media/properties/D3jLKFCcD8k-FB_IMG_1774434404646_jdnenp	2026-03-25 10:33:26.651767+00	34
35	https://res.cloudinary.com/dhqsdzxkn/image/upload/v1/media/properties/TZDNXmupuFA-FB_IMG_1774434405110_tcyo7p	2026-03-25 10:33:27.107245+00	34
36	https://res.cloudinary.com/dhqsdzxkn/image/upload/v1/media/properties/lg9hRFDHasE-FB_IMG_1774434397411_feiwp7	2026-03-25 10:33:27.739021+00	34
37	https://res.cloudinary.com/dhqsdzxkn/image/upload/v1/media/properties/pGhxLwsBO-Y-FB_IMG_1774435055185_jgwvxv	2026-03-25 10:39:08.521737+00	37
38	https://res.cloudinary.com/dhqsdzxkn/image/upload/v1/media/properties/dtBcdqdyHQA-FB_IMG_1774435052421_pgcnr4	2026-03-25 10:39:09.107651+00	37
39	https://res.cloudinary.com/dhqsdzxkn/image/upload/v1/media/properties/-t40XpAHd84-FB_IMG_1774435050216_mhcevm	2026-03-25 10:39:09.903991+00	37
40	https://res.cloudinary.com/dhqsdzxkn/image/upload/v1/media/properties/hZkkHnDVyOY-FB_IMG_1774435048198_ftottj	2026-03-25 10:39:10.562655+00	37
41	https://res.cloudinary.com/dhqsdzxkn/image/upload/v1/media/properties/7Tc95gT-SXA-FB_IMG_1774435046059_qizltr	2026-03-25 10:39:11.432981+00	37
42	https://res.cloudinary.com/dhqsdzxkn/image/upload/v1/media/properties/LMDoAuo0fsg-FB_IMG_1774435043314_acubpc	2026-03-25 10:39:14.320714+00	37
43	https://res.cloudinary.com/dhqsdzxkn/image/upload/v1/media/properties/7UCPrzQXXac-FB_IMG_1774435040454_ywm8ru	2026-03-25 10:39:14.838686+00	37
44	https://res.cloudinary.com/dhqsdzxkn/image/upload/v1/media/properties/ewAIN-cAZlM-FB_IMG_1774435037145_gcmepn	2026-03-25 10:39:15.589163+00	37
45	https://res.cloudinary.com/dhqsdzxkn/image/upload/v1/media/properties/GAs5GOmM7bk-FB_IMG_1774435033119_iarn2g	2026-03-25 10:39:16.137013+00	37
46	https://res.cloudinary.com/dhqsdzxkn/image/upload/v1/media/properties/uVqLnE6Ycnw-FB_IMG_1774435030897_ihotz5	2026-03-25 10:39:16.592369+00	37
47	https://res.cloudinary.com/dhqsdzxkn/image/upload/v1/media/properties/wAwIswMbHdE-FB_IMG_1774435264493_xjdapy	2026-03-25 10:41:46.094799+00	38
48	https://res.cloudinary.com/dhqsdzxkn/image/upload/v1/media/properties/admlFIxhZwc-FB_IMG_1774435262693_ca7f77	2026-03-25 10:41:46.620227+00	38
49	https://res.cloudinary.com/dhqsdzxkn/image/upload/v1/media/properties/cxTFJbMb6TU-FB_IMG_1774435260696_aujreu	2026-03-25 10:41:48.078636+00	38
50	https://res.cloudinary.com/dhqsdzxkn/image/upload/v1/media/properties/TvVsXCueEsU-FB_IMG_1774435258529_xc6hb9	2026-03-25 10:41:48.653644+00	38
\.


--
-- Data for Name: core_service; Type: TABLE DATA; Schema: public; Owner: u2vbp82enb8hvq
--

COPY public.core_service (id, name, description, active, created_at, updated_at, image) FROM stdin;
\.


--
-- Data for Name: core_serviceimage; Type: TABLE DATA; Schema: public; Owner: u2vbp82enb8hvq
--

COPY public.core_serviceimage (id, image, created_at, service_id) FROM stdin;
\.


--
-- Data for Name: django_admin_log; Type: TABLE DATA; Schema: public; Owner: u2vbp82enb8hvq
--

COPY public.django_admin_log (id, action_time, object_id, object_repr, action_flag, change_message, content_type_id, user_id) FROM stdin;
1	2026-03-24 11:22:51.757549+00	1	thisname1	1	[{"added": {}}]	10	1
34	2026-03-25 02:04:44.632702+00	3	agen2@l.com	3		4	1
35	2026-03-25 02:04:44.632739+00	5	agent4@l.com	3		4	1
36	2026-03-25 02:04:44.632761+00	6	agent5@l.com	3		4	1
37	2026-03-25 02:04:44.63277+00	7	agent5@L.com	3		4	1
38	2026-03-25 02:04:44.632778+00	2	agent@l.com	3		4	1
39	2026-03-25 02:04:44.632786+00	8	a@l.om	3		4	1
40	2026-03-25 02:04:44.632794+00	4	thisisagent3@gmai.com	3		4	1
41	2026-03-25 02:05:17.999669+00	9	damcfrealtyinc@gmail.com	2	[{"changed": {"fields": ["password"]}}]	4	1
42	2026-03-25 02:05:52.012284+00	9	damcfrealtyinc@gmail.com	2	[{"changed": {"fields": ["Staff status", "Superuser status"]}}]	4	1
43	2026-03-25 06:27:07.731626+00	21	jj	3		7	1
44	2026-03-25 06:27:07.731795+00	16	joe	3		7	1
45	2026-03-25 06:27:07.731835+00	20	mark	3		7	1
46	2026-03-25 06:28:01.122129+00	22	agent1	3		7	1
47	2026-03-25 06:28:31.127164+00	10	dayo_john16@yahoo.com	3		4	1
48	2026-03-25 06:28:31.127339+00	11	johnwebsiteprojects@gmail.com	3		4	1
49	2026-03-25 06:28:31.1274+00	12	myworldisadigitallife@gmail.com	3		4	1
50	2026-03-25 06:33:19.123155+00	13	dayo_john16@yahoo.com	3		4	1
51	2026-03-25 06:33:19.123224+00	14	johnwebsiteprojects@gmail.com	3		4	1
52	2026-03-25 06:33:19.269777+00	13	dayo_john16@yahoo.com	3		4	1
53	2026-03-25 06:33:19.26987+00	14	johnwebsiteprojects@gmail.com	3		4	1
54	2026-03-25 06:33:44.879129+00	23	agent1	3		7	1
55	2026-03-25 06:33:44.87934+00	24	agent2	3		7	1
56	2026-03-25 06:37:41.43946+00	15	dayo_john16@yahoo.com	3		4	1
57	2026-03-25 06:37:41.439647+00	16	johnwebsiteprojects@gmail.com	3		4	1
58	2026-03-25 06:38:01.389584+00	25	agen3	3		7	1
59	2026-03-25 06:38:01.389705+00	26	agent4	3		7	1
60	2026-03-25 06:44:21.020987+00	28	from heroku	3		7	1
61	2026-03-25 06:44:21.021026+00	27	jcccc	3		7	1
62	2026-03-25 06:44:32.999395+00	17	dayo_john16@yahoo.com	3		4	1
63	2026-03-25 06:44:32.999466+00	18	myworldisadigitallife@gmail.com	3		4	1
64	2026-03-25 10:28:52.55382+00	1	thisname1	3		10	9
65	2026-03-25 10:29:04.593069+00	34	Burgos	1	[{"added": {}}]	10	9
66	2026-03-25 10:29:22.121039+00	35	Dapa	1	[{"added": {}}]	10	9
67	2026-03-25 10:29:38.147581+00	36	Del Carmen	1	[{"added": {}}]	10	9
68	2026-03-25 10:29:54.580806+00	37	General Luna	1	[{"added": {}}]	10	9
69	2026-03-25 10:30:21.705843+00	38	Pilar	1	[{"added": {}}]	10	9
70	2026-03-25 10:30:39.154482+00	39	San Benito	1	[{"added": {}}]	10	9
71	2026-03-25 10:30:54.68031+00	40	San Isidro	1	[{"added": {}}]	10	9
72	2026-03-25 10:31:09.523882+00	41	Santa Monica	1	[{"added": {}}]	10	9
73	2026-03-25 10:31:21.806113+00	42	Socorro	1	[{"added": {}}]	10	9
\.


--
-- Data for Name: django_content_type; Type: TABLE DATA; Schema: public; Owner: u2vbp82enb8hvq
--

COPY public.django_content_type (id, app_label, model) FROM stdin;
1	admin	logentry
2	auth	group
3	auth	permission
4	auth	user
5	contenttypes	contenttype
6	sessions	session
7	core	agent
8	core	bookingrequest
9	core	contactmessage
10	core	municipality
11	core	note
12	core	property
13	core	propertyimage
14	core	service
15	core	serviceimage
\.


--
-- Data for Name: django_migrations; Type: TABLE DATA; Schema: public; Owner: u2vbp82enb8hvq
--

COPY public.django_migrations (id, app, name, applied) FROM stdin;
1	contenttypes	0001_initial	2026-03-24 02:03:05.27641+00
2	auth	0001_initial	2026-03-24 02:03:05.433575+00
3	admin	0001_initial	2026-03-24 02:03:05.48396+00
4	admin	0002_logentry_remove_auto_add	2026-03-24 02:03:05.493087+00
5	admin	0003_logentry_add_action_flag_choices	2026-03-24 02:03:05.502069+00
6	contenttypes	0002_remove_content_type_name	2026-03-24 02:03:05.52163+00
7	auth	0002_alter_permission_name_max_length	2026-03-24 02:03:05.531621+00
8	auth	0003_alter_user_email_max_length	2026-03-24 02:03:05.542541+00
9	auth	0004_alter_user_username_opts	2026-03-24 02:03:05.552205+00
10	auth	0005_alter_user_last_login_null	2026-03-24 02:03:05.562492+00
11	auth	0006_require_contenttypes_0002	2026-03-24 02:03:05.567224+00
12	auth	0007_alter_validators_add_error_messages	2026-03-24 02:03:05.575141+00
13	auth	0008_alter_user_username_max_length	2026-03-24 02:03:05.604662+00
14	auth	0009_alter_user_last_name_max_length	2026-03-24 02:03:05.617887+00
15	auth	0010_alter_group_name_max_length	2026-03-24 02:03:05.632728+00
16	auth	0011_update_proxy_permissions	2026-03-24 02:03:05.64567+00
17	auth	0012_alter_user_first_name_max_length	2026-03-24 02:03:05.657741+00
18	core	0001_initial	2026-03-24 02:03:05.678455+00
19	core	0002_property_propertyimage	2026-03-24 02:03:05.832848+00
20	core	0003_contactmessage	2026-03-24 02:03:05.895386+00
21	core	0004_agent	2026-03-24 02:03:05.938824+00
22	core	0005_agents_group	2026-03-24 02:03:05.976588+00
23	core	0006_property_created_by	2026-03-24 02:03:06.02663+00
24	core	0007_agent_properties_agent_user_alter_property_status	2026-03-24 02:03:06.210289+00
25	core	0008_municipality_property_municipality	2026-03-24 02:03:06.37635+00
26	core	0009_municipality_description	2026-03-24 02:03:06.444679+00
27	core	0010_service	2026-03-24 02:03:06.543264+00
28	core	0011_alter_agent_photo_alter_propertyimage_image	2026-03-24 02:03:06.594827+00
29	core	0012_bookingrequest	2026-03-24 02:03:06.697047+00
30	core	0013_property_is_featured	2026-03-24 02:03:06.744729+00
31	core	0014_service_image	2026-03-24 02:03:06.806984+00
32	core	0015_serviceimage	2026-03-24 02:03:06.96689+00
33	sessions	0001_initial	2026-03-24 02:03:07.048764+00
\.


--
-- Data for Name: django_session; Type: TABLE DATA; Schema: public; Owner: u2vbp82enb8hvq
--

COPY public.django_session (session_key, session_data, expire_date) FROM stdin;
1nocqigplko3vjcv9ysbmd5sliy240bo	.eJxVjMsOwiAQRf-FtSEM8mhduu83kBkGpGogKe3K-O_apAvd3nPOfYmA21rC1tMSZhYXAeL0uxHGR6o74DvWW5Ox1XWZSe6KPGiXU-P0vB7u30HBXr51UpqsIWBFbvDgkoLI5G0eERCUhuhTRGMHOzrDZ2BvyBIyGh0N5izeH-C-OEE:1w4zwu:rPNTePrdAei9Unyq4qdlau3O_PVj1Y1OWFbHABgT8SA	2026-04-07 11:29:28.338539+00
v2h1b5yp9rk140n6mzxteo4kz63bsc1g	.eJxVjMEOwiAQRP-FsyHgsqAevfsNZGEXqZqSlPZk_HfbpAe9Tea9mbeKtMw1Ll2mOLC6KKsOv12i_JRxA_yg8d50buM8DUlvit5p17fG8rru7t9BpV7XdSm2eDgLiMlIgWiNCeHEwRkuJEdDVhADswvgrRj0ji0kKpIRANXnC__bOFc:1w509F:-1Qwr5klbukmW99MleIKnPv04sEHc5d8gJzxxnQKWAI	2026-04-07 11:42:13.902272+00
zltaq2zvc8t3n20tzuce2l7enp7izbas	.eJxVjDsOwjAQBe_iGllO7PWHkp4zRLvrDQ4gW8qnQtwdIqWA9s3Me6kBt7UM2yLzMGV1Vp06_W6E_JC6g3zHemuaW13nifSu6IMu-tqyPC-H-3dQcCnfmimZHJIJLvdx7ANYQwhC3jsjSJAyRxLwEYwVOzrjLHgOnSAk5MTq_QHd0TfY:1w50LU:H4k3oL0oxg9PgkxoFOYF50kgGTr-39S3-EUNi3k7IMA	2026-04-07 11:54:52.777394+00
bo6w07fvo3hv3v5dw7q6p4iiqdy8offv	.eJxVjDsOwjAQBe_iGllO7PWHkp4zRLvrDQ4gW8qnQtwdIqWA9s3Me6kBt7UM2yLzMGV1Vp06_W6E_JC6g3zHemuaW13nifSu6IMu-tqyPC-H-3dQcCnfmimZHJIJLvdx7ANYQwhC3jsjSJAyRxLwEYwVOzrjLHgOnSAk5MTq_QHd0TfY:1w50Z2:AhVzoeSbldwcHDbezdDWc3Qemg-PYNx6I_e5WaJip0M	2026-04-07 12:08:52.254665+00
evnx1i26fhxef7mt2ihdeqiks2i9k17m	.eJxVjEsOwjAMBe-SNYqS2E0KS_Y9Q-TYLi2gVOpnhbg7VOoCtm9m3stk2tYhb4vOeRRzMd6cfrdC_NC6A7lTvU2Wp7rOY7G7Yg-62G4SfV4P9-9goGX41n1JwRNiKvHM7JrQOmigBYgMrKiYsGXwQth7jD4WDxQZA4moJNeY9wfHUzde:1w5HvX:fgOMfBCEXcEEKRbgFYtLPadw913J7MWTg0LpKP0xY1k	2026-04-08 06:41:15.501776+00
\.


--
-- Name: auth_group_id_seq; Type: SEQUENCE SET; Schema: public; Owner: u2vbp82enb8hvq
--

SELECT pg_catalog.setval('public.auth_group_id_seq', 33, true);


--
-- Name: auth_group_permissions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: u2vbp82enb8hvq
--

SELECT pg_catalog.setval('public.auth_group_permissions_id_seq', 1, false);


--
-- Name: auth_permission_id_seq; Type: SEQUENCE SET; Schema: public; Owner: u2vbp82enb8hvq
--

SELECT pg_catalog.setval('public.auth_permission_id_seq', 66, true);


--
-- Name: auth_user_groups_id_seq; Type: SEQUENCE SET; Schema: public; Owner: u2vbp82enb8hvq
--

SELECT pg_catalog.setval('public.auth_user_groups_id_seq', 66, true);


--
-- Name: auth_user_id_seq; Type: SEQUENCE SET; Schema: public; Owner: u2vbp82enb8hvq
--

SELECT pg_catalog.setval('public.auth_user_id_seq', 33, true);


--
-- Name: auth_user_user_permissions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: u2vbp82enb8hvq
--

SELECT pg_catalog.setval('public.auth_user_user_permissions_id_seq', 1, false);


--
-- Name: core_agent_id_seq; Type: SEQUENCE SET; Schema: public; Owner: u2vbp82enb8hvq
--

SELECT pg_catalog.setval('public.core_agent_id_seq', 33, true);


--
-- Name: core_agent_properties_id_seq; Type: SEQUENCE SET; Schema: public; Owner: u2vbp82enb8hvq
--

SELECT pg_catalog.setval('public.core_agent_properties_id_seq', 33, true);


--
-- Name: core_bookingrequest_id_seq; Type: SEQUENCE SET; Schema: public; Owner: u2vbp82enb8hvq
--

SELECT pg_catalog.setval('public.core_bookingrequest_id_seq', 1, false);


--
-- Name: core_contactmessage_id_seq; Type: SEQUENCE SET; Schema: public; Owner: u2vbp82enb8hvq
--

SELECT pg_catalog.setval('public.core_contactmessage_id_seq', 33, true);


--
-- Name: core_municipality_id_seq; Type: SEQUENCE SET; Schema: public; Owner: u2vbp82enb8hvq
--

SELECT pg_catalog.setval('public.core_municipality_id_seq', 66, true);


--
-- Name: core_municipality_properties_id_seq; Type: SEQUENCE SET; Schema: public; Owner: u2vbp82enb8hvq
--

SELECT pg_catalog.setval('public.core_municipality_properties_id_seq', 66, true);


--
-- Name: core_note_id_seq; Type: SEQUENCE SET; Schema: public; Owner: u2vbp82enb8hvq
--

SELECT pg_catalog.setval('public.core_note_id_seq', 1, false);


--
-- Name: core_property_id_seq; Type: SEQUENCE SET; Schema: public; Owner: u2vbp82enb8hvq
--

SELECT pg_catalog.setval('public.core_property_id_seq', 66, true);


--
-- Name: core_propertyimage_id_seq; Type: SEQUENCE SET; Schema: public; Owner: u2vbp82enb8hvq
--

SELECT pg_catalog.setval('public.core_propertyimage_id_seq', 66, true);


--
-- Name: core_service_id_seq; Type: SEQUENCE SET; Schema: public; Owner: u2vbp82enb8hvq
--

SELECT pg_catalog.setval('public.core_service_id_seq', 1, false);


--
-- Name: core_serviceimage_id_seq; Type: SEQUENCE SET; Schema: public; Owner: u2vbp82enb8hvq
--

SELECT pg_catalog.setval('public.core_serviceimage_id_seq', 1, false);


--
-- Name: django_admin_log_id_seq; Type: SEQUENCE SET; Schema: public; Owner: u2vbp82enb8hvq
--

SELECT pg_catalog.setval('public.django_admin_log_id_seq', 99, true);


--
-- Name: django_content_type_id_seq; Type: SEQUENCE SET; Schema: public; Owner: u2vbp82enb8hvq
--

SELECT pg_catalog.setval('public.django_content_type_id_seq', 33, true);


--
-- Name: django_migrations_id_seq; Type: SEQUENCE SET; Schema: public; Owner: u2vbp82enb8hvq
--

SELECT pg_catalog.setval('public.django_migrations_id_seq', 33, true);


--
-- Name: auth_group auth_group_name_key; Type: CONSTRAINT; Schema: public; Owner: u2vbp82enb8hvq
--

ALTER TABLE ONLY public.auth_group
    ADD CONSTRAINT auth_group_name_key UNIQUE (name);


--
-- Name: auth_group_permissions auth_group_permissions_group_id_permission_id_0cd325b0_uniq; Type: CONSTRAINT; Schema: public; Owner: u2vbp82enb8hvq
--

ALTER TABLE ONLY public.auth_group_permissions
    ADD CONSTRAINT auth_group_permissions_group_id_permission_id_0cd325b0_uniq UNIQUE (group_id, permission_id);


--
-- Name: auth_group_permissions auth_group_permissions_pkey; Type: CONSTRAINT; Schema: public; Owner: u2vbp82enb8hvq
--

ALTER TABLE ONLY public.auth_group_permissions
    ADD CONSTRAINT auth_group_permissions_pkey PRIMARY KEY (id);


--
-- Name: auth_group auth_group_pkey; Type: CONSTRAINT; Schema: public; Owner: u2vbp82enb8hvq
--

ALTER TABLE ONLY public.auth_group
    ADD CONSTRAINT auth_group_pkey PRIMARY KEY (id);


--
-- Name: auth_permission auth_permission_content_type_id_codename_01ab375a_uniq; Type: CONSTRAINT; Schema: public; Owner: u2vbp82enb8hvq
--

ALTER TABLE ONLY public.auth_permission
    ADD CONSTRAINT auth_permission_content_type_id_codename_01ab375a_uniq UNIQUE (content_type_id, codename);


--
-- Name: auth_permission auth_permission_pkey; Type: CONSTRAINT; Schema: public; Owner: u2vbp82enb8hvq
--

ALTER TABLE ONLY public.auth_permission
    ADD CONSTRAINT auth_permission_pkey PRIMARY KEY (id);


--
-- Name: auth_user_groups auth_user_groups_pkey; Type: CONSTRAINT; Schema: public; Owner: u2vbp82enb8hvq
--

ALTER TABLE ONLY public.auth_user_groups
    ADD CONSTRAINT auth_user_groups_pkey PRIMARY KEY (id);


--
-- Name: auth_user_groups auth_user_groups_user_id_group_id_94350c0c_uniq; Type: CONSTRAINT; Schema: public; Owner: u2vbp82enb8hvq
--

ALTER TABLE ONLY public.auth_user_groups
    ADD CONSTRAINT auth_user_groups_user_id_group_id_94350c0c_uniq UNIQUE (user_id, group_id);


--
-- Name: auth_user auth_user_pkey; Type: CONSTRAINT; Schema: public; Owner: u2vbp82enb8hvq
--

ALTER TABLE ONLY public.auth_user
    ADD CONSTRAINT auth_user_pkey PRIMARY KEY (id);


--
-- Name: auth_user_user_permissions auth_user_user_permissions_pkey; Type: CONSTRAINT; Schema: public; Owner: u2vbp82enb8hvq
--

ALTER TABLE ONLY public.auth_user_user_permissions
    ADD CONSTRAINT auth_user_user_permissions_pkey PRIMARY KEY (id);


--
-- Name: auth_user_user_permissions auth_user_user_permissions_user_id_permission_id_14a6b632_uniq; Type: CONSTRAINT; Schema: public; Owner: u2vbp82enb8hvq
--

ALTER TABLE ONLY public.auth_user_user_permissions
    ADD CONSTRAINT auth_user_user_permissions_user_id_permission_id_14a6b632_uniq UNIQUE (user_id, permission_id);


--
-- Name: auth_user auth_user_username_key; Type: CONSTRAINT; Schema: public; Owner: u2vbp82enb8hvq
--

ALTER TABLE ONLY public.auth_user
    ADD CONSTRAINT auth_user_username_key UNIQUE (username);


--
-- Name: core_agent core_agent_pkey; Type: CONSTRAINT; Schema: public; Owner: u2vbp82enb8hvq
--

ALTER TABLE ONLY public.core_agent
    ADD CONSTRAINT core_agent_pkey PRIMARY KEY (id);


--
-- Name: core_agent_properties core_agent_properties_agent_id_property_id_2dfe0baa_uniq; Type: CONSTRAINT; Schema: public; Owner: u2vbp82enb8hvq
--

ALTER TABLE ONLY public.core_agent_properties
    ADD CONSTRAINT core_agent_properties_agent_id_property_id_2dfe0baa_uniq UNIQUE (agent_id, property_id);


--
-- Name: core_agent_properties core_agent_properties_pkey; Type: CONSTRAINT; Schema: public; Owner: u2vbp82enb8hvq
--

ALTER TABLE ONLY public.core_agent_properties
    ADD CONSTRAINT core_agent_properties_pkey PRIMARY KEY (id);


--
-- Name: core_agent core_agent_user_id_key; Type: CONSTRAINT; Schema: public; Owner: u2vbp82enb8hvq
--

ALTER TABLE ONLY public.core_agent
    ADD CONSTRAINT core_agent_user_id_key UNIQUE (user_id);


--
-- Name: core_bookingrequest core_bookingrequest_pkey; Type: CONSTRAINT; Schema: public; Owner: u2vbp82enb8hvq
--

ALTER TABLE ONLY public.core_bookingrequest
    ADD CONSTRAINT core_bookingrequest_pkey PRIMARY KEY (id);


--
-- Name: core_contactmessage core_contactmessage_pkey; Type: CONSTRAINT; Schema: public; Owner: u2vbp82enb8hvq
--

ALTER TABLE ONLY public.core_contactmessage
    ADD CONSTRAINT core_contactmessage_pkey PRIMARY KEY (id);


--
-- Name: core_municipality core_municipality_name_key; Type: CONSTRAINT; Schema: public; Owner: u2vbp82enb8hvq
--

ALTER TABLE ONLY public.core_municipality
    ADD CONSTRAINT core_municipality_name_key UNIQUE (name);


--
-- Name: core_municipality core_municipality_pkey; Type: CONSTRAINT; Schema: public; Owner: u2vbp82enb8hvq
--

ALTER TABLE ONLY public.core_municipality
    ADD CONSTRAINT core_municipality_pkey PRIMARY KEY (id);


--
-- Name: core_municipality_properties core_municipality_proper_municipality_id_property_e02ac212_uniq; Type: CONSTRAINT; Schema: public; Owner: u2vbp82enb8hvq
--

ALTER TABLE ONLY public.core_municipality_properties
    ADD CONSTRAINT core_municipality_proper_municipality_id_property_e02ac212_uniq UNIQUE (municipality_id, property_id);


--
-- Name: core_municipality_properties core_municipality_properties_pkey; Type: CONSTRAINT; Schema: public; Owner: u2vbp82enb8hvq
--

ALTER TABLE ONLY public.core_municipality_properties
    ADD CONSTRAINT core_municipality_properties_pkey PRIMARY KEY (id);


--
-- Name: core_note core_note_pkey; Type: CONSTRAINT; Schema: public; Owner: u2vbp82enb8hvq
--

ALTER TABLE ONLY public.core_note
    ADD CONSTRAINT core_note_pkey PRIMARY KEY (id);


--
-- Name: core_property core_property_pkey; Type: CONSTRAINT; Schema: public; Owner: u2vbp82enb8hvq
--

ALTER TABLE ONLY public.core_property
    ADD CONSTRAINT core_property_pkey PRIMARY KEY (id);


--
-- Name: core_propertyimage core_propertyimage_pkey; Type: CONSTRAINT; Schema: public; Owner: u2vbp82enb8hvq
--

ALTER TABLE ONLY public.core_propertyimage
    ADD CONSTRAINT core_propertyimage_pkey PRIMARY KEY (id);


--
-- Name: core_service core_service_name_key; Type: CONSTRAINT; Schema: public; Owner: u2vbp82enb8hvq
--

ALTER TABLE ONLY public.core_service
    ADD CONSTRAINT core_service_name_key UNIQUE (name);


--
-- Name: core_service core_service_pkey; Type: CONSTRAINT; Schema: public; Owner: u2vbp82enb8hvq
--

ALTER TABLE ONLY public.core_service
    ADD CONSTRAINT core_service_pkey PRIMARY KEY (id);


--
-- Name: core_serviceimage core_serviceimage_pkey; Type: CONSTRAINT; Schema: public; Owner: u2vbp82enb8hvq
--

ALTER TABLE ONLY public.core_serviceimage
    ADD CONSTRAINT core_serviceimage_pkey PRIMARY KEY (id);


--
-- Name: django_admin_log django_admin_log_pkey; Type: CONSTRAINT; Schema: public; Owner: u2vbp82enb8hvq
--

ALTER TABLE ONLY public.django_admin_log
    ADD CONSTRAINT django_admin_log_pkey PRIMARY KEY (id);


--
-- Name: django_content_type django_content_type_app_label_model_76bd3d3b_uniq; Type: CONSTRAINT; Schema: public; Owner: u2vbp82enb8hvq
--

ALTER TABLE ONLY public.django_content_type
    ADD CONSTRAINT django_content_type_app_label_model_76bd3d3b_uniq UNIQUE (app_label, model);


--
-- Name: django_content_type django_content_type_pkey; Type: CONSTRAINT; Schema: public; Owner: u2vbp82enb8hvq
--

ALTER TABLE ONLY public.django_content_type
    ADD CONSTRAINT django_content_type_pkey PRIMARY KEY (id);


--
-- Name: django_migrations django_migrations_pkey; Type: CONSTRAINT; Schema: public; Owner: u2vbp82enb8hvq
--

ALTER TABLE ONLY public.django_migrations
    ADD CONSTRAINT django_migrations_pkey PRIMARY KEY (id);


--
-- Name: django_session django_session_pkey; Type: CONSTRAINT; Schema: public; Owner: u2vbp82enb8hvq
--

ALTER TABLE ONLY public.django_session
    ADD CONSTRAINT django_session_pkey PRIMARY KEY (session_key);


--
-- Name: auth_group_name_a6ea08ec_like; Type: INDEX; Schema: public; Owner: u2vbp82enb8hvq
--

CREATE INDEX auth_group_name_a6ea08ec_like ON public.auth_group USING btree (name varchar_pattern_ops);


--
-- Name: auth_group_permissions_group_id_b120cbf9; Type: INDEX; Schema: public; Owner: u2vbp82enb8hvq
--

CREATE INDEX auth_group_permissions_group_id_b120cbf9 ON public.auth_group_permissions USING btree (group_id);


--
-- Name: auth_group_permissions_permission_id_84c5c92e; Type: INDEX; Schema: public; Owner: u2vbp82enb8hvq
--

CREATE INDEX auth_group_permissions_permission_id_84c5c92e ON public.auth_group_permissions USING btree (permission_id);


--
-- Name: auth_permission_content_type_id_2f476e4b; Type: INDEX; Schema: public; Owner: u2vbp82enb8hvq
--

CREATE INDEX auth_permission_content_type_id_2f476e4b ON public.auth_permission USING btree (content_type_id);


--
-- Name: auth_user_groups_group_id_97559544; Type: INDEX; Schema: public; Owner: u2vbp82enb8hvq
--

CREATE INDEX auth_user_groups_group_id_97559544 ON public.auth_user_groups USING btree (group_id);


--
-- Name: auth_user_groups_user_id_6a12ed8b; Type: INDEX; Schema: public; Owner: u2vbp82enb8hvq
--

CREATE INDEX auth_user_groups_user_id_6a12ed8b ON public.auth_user_groups USING btree (user_id);


--
-- Name: auth_user_user_permissions_permission_id_1fbb5f2c; Type: INDEX; Schema: public; Owner: u2vbp82enb8hvq
--

CREATE INDEX auth_user_user_permissions_permission_id_1fbb5f2c ON public.auth_user_user_permissions USING btree (permission_id);


--
-- Name: auth_user_user_permissions_user_id_a95ead1b; Type: INDEX; Schema: public; Owner: u2vbp82enb8hvq
--

CREATE INDEX auth_user_user_permissions_user_id_a95ead1b ON public.auth_user_user_permissions USING btree (user_id);


--
-- Name: auth_user_username_6821ab7c_like; Type: INDEX; Schema: public; Owner: u2vbp82enb8hvq
--

CREATE INDEX auth_user_username_6821ab7c_like ON public.auth_user USING btree (username varchar_pattern_ops);


--
-- Name: core_agent_properties_agent_id_78f3be40; Type: INDEX; Schema: public; Owner: u2vbp82enb8hvq
--

CREATE INDEX core_agent_properties_agent_id_78f3be40 ON public.core_agent_properties USING btree (agent_id);


--
-- Name: core_agent_properties_property_id_a649bdd8; Type: INDEX; Schema: public; Owner: u2vbp82enb8hvq
--

CREATE INDEX core_agent_properties_property_id_a649bdd8 ON public.core_agent_properties USING btree (property_id);


--
-- Name: core_bookingrequest_property_id_b50046ea; Type: INDEX; Schema: public; Owner: u2vbp82enb8hvq
--

CREATE INDEX core_bookingrequest_property_id_b50046ea ON public.core_bookingrequest USING btree (property_id);


--
-- Name: core_municipality_name_303f26f3_like; Type: INDEX; Schema: public; Owner: u2vbp82enb8hvq
--

CREATE INDEX core_municipality_name_303f26f3_like ON public.core_municipality USING btree (name varchar_pattern_ops);


--
-- Name: core_municipality_properties_municipality_id_1b457a43; Type: INDEX; Schema: public; Owner: u2vbp82enb8hvq
--

CREATE INDEX core_municipality_properties_municipality_id_1b457a43 ON public.core_municipality_properties USING btree (municipality_id);


--
-- Name: core_municipality_properties_property_id_815743d6; Type: INDEX; Schema: public; Owner: u2vbp82enb8hvq
--

CREATE INDEX core_municipality_properties_property_id_815743d6 ON public.core_municipality_properties USING btree (property_id);


--
-- Name: core_property_created_by_id_2c776074; Type: INDEX; Schema: public; Owner: u2vbp82enb8hvq
--

CREATE INDEX core_property_created_by_id_2c776074 ON public.core_property USING btree (created_by_id);


--
-- Name: core_property_municipality_id_eda1cede; Type: INDEX; Schema: public; Owner: u2vbp82enb8hvq
--

CREATE INDEX core_property_municipality_id_eda1cede ON public.core_property USING btree (municipality_id);


--
-- Name: core_propertyimage_property_id_86e80a6a; Type: INDEX; Schema: public; Owner: u2vbp82enb8hvq
--

CREATE INDEX core_propertyimage_property_id_86e80a6a ON public.core_propertyimage USING btree (property_id);


--
-- Name: core_service_name_8e9e4033_like; Type: INDEX; Schema: public; Owner: u2vbp82enb8hvq
--

CREATE INDEX core_service_name_8e9e4033_like ON public.core_service USING btree (name varchar_pattern_ops);


--
-- Name: core_serviceimage_service_id_1c8958c2; Type: INDEX; Schema: public; Owner: u2vbp82enb8hvq
--

CREATE INDEX core_serviceimage_service_id_1c8958c2 ON public.core_serviceimage USING btree (service_id);


--
-- Name: django_admin_log_content_type_id_c4bce8eb; Type: INDEX; Schema: public; Owner: u2vbp82enb8hvq
--

CREATE INDEX django_admin_log_content_type_id_c4bce8eb ON public.django_admin_log USING btree (content_type_id);


--
-- Name: django_admin_log_user_id_c564eba6; Type: INDEX; Schema: public; Owner: u2vbp82enb8hvq
--

CREATE INDEX django_admin_log_user_id_c564eba6 ON public.django_admin_log USING btree (user_id);


--
-- Name: django_session_expire_date_a5c62663; Type: INDEX; Schema: public; Owner: u2vbp82enb8hvq
--

CREATE INDEX django_session_expire_date_a5c62663 ON public.django_session USING btree (expire_date);


--
-- Name: django_session_session_key_c0390e0f_like; Type: INDEX; Schema: public; Owner: u2vbp82enb8hvq
--

CREATE INDEX django_session_session_key_c0390e0f_like ON public.django_session USING btree (session_key varchar_pattern_ops);


--
-- Name: auth_group_permissions auth_group_permissio_permission_id_84c5c92e_fk_auth_perm; Type: FK CONSTRAINT; Schema: public; Owner: u2vbp82enb8hvq
--

ALTER TABLE ONLY public.auth_group_permissions
    ADD CONSTRAINT auth_group_permissio_permission_id_84c5c92e_fk_auth_perm FOREIGN KEY (permission_id) REFERENCES public.auth_permission(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: auth_group_permissions auth_group_permissions_group_id_b120cbf9_fk_auth_group_id; Type: FK CONSTRAINT; Schema: public; Owner: u2vbp82enb8hvq
--

ALTER TABLE ONLY public.auth_group_permissions
    ADD CONSTRAINT auth_group_permissions_group_id_b120cbf9_fk_auth_group_id FOREIGN KEY (group_id) REFERENCES public.auth_group(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: auth_permission auth_permission_content_type_id_2f476e4b_fk_django_co; Type: FK CONSTRAINT; Schema: public; Owner: u2vbp82enb8hvq
--

ALTER TABLE ONLY public.auth_permission
    ADD CONSTRAINT auth_permission_content_type_id_2f476e4b_fk_django_co FOREIGN KEY (content_type_id) REFERENCES public.django_content_type(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: auth_user_groups auth_user_groups_group_id_97559544_fk_auth_group_id; Type: FK CONSTRAINT; Schema: public; Owner: u2vbp82enb8hvq
--

ALTER TABLE ONLY public.auth_user_groups
    ADD CONSTRAINT auth_user_groups_group_id_97559544_fk_auth_group_id FOREIGN KEY (group_id) REFERENCES public.auth_group(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: auth_user_groups auth_user_groups_user_id_6a12ed8b_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: u2vbp82enb8hvq
--

ALTER TABLE ONLY public.auth_user_groups
    ADD CONSTRAINT auth_user_groups_user_id_6a12ed8b_fk_auth_user_id FOREIGN KEY (user_id) REFERENCES public.auth_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: auth_user_user_permissions auth_user_user_permi_permission_id_1fbb5f2c_fk_auth_perm; Type: FK CONSTRAINT; Schema: public; Owner: u2vbp82enb8hvq
--

ALTER TABLE ONLY public.auth_user_user_permissions
    ADD CONSTRAINT auth_user_user_permi_permission_id_1fbb5f2c_fk_auth_perm FOREIGN KEY (permission_id) REFERENCES public.auth_permission(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: auth_user_user_permissions auth_user_user_permissions_user_id_a95ead1b_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: u2vbp82enb8hvq
--

ALTER TABLE ONLY public.auth_user_user_permissions
    ADD CONSTRAINT auth_user_user_permissions_user_id_a95ead1b_fk_auth_user_id FOREIGN KEY (user_id) REFERENCES public.auth_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_agent_properties core_agent_properties_agent_id_78f3be40_fk_core_agent_id; Type: FK CONSTRAINT; Schema: public; Owner: u2vbp82enb8hvq
--

ALTER TABLE ONLY public.core_agent_properties
    ADD CONSTRAINT core_agent_properties_agent_id_78f3be40_fk_core_agent_id FOREIGN KEY (agent_id) REFERENCES public.core_agent(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_agent_properties core_agent_properties_property_id_a649bdd8_fk_core_property_id; Type: FK CONSTRAINT; Schema: public; Owner: u2vbp82enb8hvq
--

ALTER TABLE ONLY public.core_agent_properties
    ADD CONSTRAINT core_agent_properties_property_id_a649bdd8_fk_core_property_id FOREIGN KEY (property_id) REFERENCES public.core_property(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_agent core_agent_user_id_2b665df0_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: u2vbp82enb8hvq
--

ALTER TABLE ONLY public.core_agent
    ADD CONSTRAINT core_agent_user_id_2b665df0_fk_auth_user_id FOREIGN KEY (user_id) REFERENCES public.auth_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_bookingrequest core_bookingrequest_property_id_b50046ea_fk_core_property_id; Type: FK CONSTRAINT; Schema: public; Owner: u2vbp82enb8hvq
--

ALTER TABLE ONLY public.core_bookingrequest
    ADD CONSTRAINT core_bookingrequest_property_id_b50046ea_fk_core_property_id FOREIGN KEY (property_id) REFERENCES public.core_property(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_municipality_properties core_municipality_pr_municipality_id_1b457a43_fk_core_muni; Type: FK CONSTRAINT; Schema: public; Owner: u2vbp82enb8hvq
--

ALTER TABLE ONLY public.core_municipality_properties
    ADD CONSTRAINT core_municipality_pr_municipality_id_1b457a43_fk_core_muni FOREIGN KEY (municipality_id) REFERENCES public.core_municipality(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_municipality_properties core_municipality_pr_property_id_815743d6_fk_core_prop; Type: FK CONSTRAINT; Schema: public; Owner: u2vbp82enb8hvq
--

ALTER TABLE ONLY public.core_municipality_properties
    ADD CONSTRAINT core_municipality_pr_property_id_815743d6_fk_core_prop FOREIGN KEY (property_id) REFERENCES public.core_property(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_property core_property_created_by_id_2c776074_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: u2vbp82enb8hvq
--

ALTER TABLE ONLY public.core_property
    ADD CONSTRAINT core_property_created_by_id_2c776074_fk_auth_user_id FOREIGN KEY (created_by_id) REFERENCES public.auth_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_property core_property_municipality_id_eda1cede_fk_core_municipality_id; Type: FK CONSTRAINT; Schema: public; Owner: u2vbp82enb8hvq
--

ALTER TABLE ONLY public.core_property
    ADD CONSTRAINT core_property_municipality_id_eda1cede_fk_core_municipality_id FOREIGN KEY (municipality_id) REFERENCES public.core_municipality(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_propertyimage core_propertyimage_property_id_86e80a6a_fk_core_property_id; Type: FK CONSTRAINT; Schema: public; Owner: u2vbp82enb8hvq
--

ALTER TABLE ONLY public.core_propertyimage
    ADD CONSTRAINT core_propertyimage_property_id_86e80a6a_fk_core_property_id FOREIGN KEY (property_id) REFERENCES public.core_property(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_serviceimage core_serviceimage_service_id_1c8958c2_fk_core_service_id; Type: FK CONSTRAINT; Schema: public; Owner: u2vbp82enb8hvq
--

ALTER TABLE ONLY public.core_serviceimage
    ADD CONSTRAINT core_serviceimage_service_id_1c8958c2_fk_core_service_id FOREIGN KEY (service_id) REFERENCES public.core_service(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: django_admin_log django_admin_log_content_type_id_c4bce8eb_fk_django_co; Type: FK CONSTRAINT; Schema: public; Owner: u2vbp82enb8hvq
--

ALTER TABLE ONLY public.django_admin_log
    ADD CONSTRAINT django_admin_log_content_type_id_c4bce8eb_fk_django_co FOREIGN KEY (content_type_id) REFERENCES public.django_content_type(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: django_admin_log django_admin_log_user_id_c564eba6_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: u2vbp82enb8hvq
--

ALTER TABLE ONLY public.django_admin_log
    ADD CONSTRAINT django_admin_log_user_id_c564eba6_fk_auth_user_id FOREIGN KEY (user_id) REFERENCES public.auth_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: SCHEMA public; Type: ACL; Schema: -; Owner: u2vbp82enb8hvq
--

REVOKE USAGE ON SCHEMA public FROM PUBLIC;


--
-- Name: FUNCTION pg_stat_statements(showtext boolean, OUT userid oid, OUT dbid oid, OUT toplevel boolean, OUT queryid bigint, OUT query text, OUT plans bigint, OUT total_plan_time double precision, OUT min_plan_time double precision, OUT max_plan_time double precision, OUT mean_plan_time double precision, OUT stddev_plan_time double precision, OUT calls bigint, OUT total_exec_time double precision, OUT min_exec_time double precision, OUT max_exec_time double precision, OUT mean_exec_time double precision, OUT stddev_exec_time double precision, OUT rows bigint, OUT shared_blks_hit bigint, OUT shared_blks_read bigint, OUT shared_blks_dirtied bigint, OUT shared_blks_written bigint, OUT local_blks_hit bigint, OUT local_blks_read bigint, OUT local_blks_dirtied bigint, OUT local_blks_written bigint, OUT temp_blks_read bigint, OUT temp_blks_written bigint, OUT shared_blk_read_time double precision, OUT shared_blk_write_time double precision, OUT local_blk_read_time double precision, OUT local_blk_write_time double precision, OUT temp_blk_read_time double precision, OUT temp_blk_write_time double precision, OUT wal_records bigint, OUT wal_fpi bigint, OUT wal_bytes numeric, OUT jit_functions bigint, OUT jit_generation_time double precision, OUT jit_inlining_count bigint, OUT jit_inlining_time double precision, OUT jit_optimization_count bigint, OUT jit_optimization_time double precision, OUT jit_emission_count bigint, OUT jit_emission_time double precision, OUT jit_deform_count bigint, OUT jit_deform_time double precision, OUT stats_since timestamp with time zone, OUT minmax_stats_since timestamp with time zone); Type: ACL; Schema: public; Owner: rdsadmin
--

GRANT ALL ON FUNCTION public.pg_stat_statements(showtext boolean, OUT userid oid, OUT dbid oid, OUT toplevel boolean, OUT queryid bigint, OUT query text, OUT plans bigint, OUT total_plan_time double precision, OUT min_plan_time double precision, OUT max_plan_time double precision, OUT mean_plan_time double precision, OUT stddev_plan_time double precision, OUT calls bigint, OUT total_exec_time double precision, OUT min_exec_time double precision, OUT max_exec_time double precision, OUT mean_exec_time double precision, OUT stddev_exec_time double precision, OUT rows bigint, OUT shared_blks_hit bigint, OUT shared_blks_read bigint, OUT shared_blks_dirtied bigint, OUT shared_blks_written bigint, OUT local_blks_hit bigint, OUT local_blks_read bigint, OUT local_blks_dirtied bigint, OUT local_blks_written bigint, OUT temp_blks_read bigint, OUT temp_blks_written bigint, OUT shared_blk_read_time double precision, OUT shared_blk_write_time double precision, OUT local_blk_read_time double precision, OUT local_blk_write_time double precision, OUT temp_blk_read_time double precision, OUT temp_blk_write_time double precision, OUT wal_records bigint, OUT wal_fpi bigint, OUT wal_bytes numeric, OUT jit_functions bigint, OUT jit_generation_time double precision, OUT jit_inlining_count bigint, OUT jit_inlining_time double precision, OUT jit_optimization_count bigint, OUT jit_optimization_time double precision, OUT jit_emission_count bigint, OUT jit_emission_time double precision, OUT jit_deform_count bigint, OUT jit_deform_time double precision, OUT stats_since timestamp with time zone, OUT minmax_stats_since timestamp with time zone) TO u2vbp82enb8hvq;


--
-- Name: FUNCTION pg_stat_statements_info(OUT dealloc bigint, OUT stats_reset timestamp with time zone); Type: ACL; Schema: public; Owner: rdsadmin
--

GRANT ALL ON FUNCTION public.pg_stat_statements_info(OUT dealloc bigint, OUT stats_reset timestamp with time zone) TO u2vbp82enb8hvq;


--
-- Name: FUNCTION pg_stat_statements_reset(userid oid, dbid oid, queryid bigint, minmax_only boolean); Type: ACL; Schema: public; Owner: rdsadmin
--

GRANT ALL ON FUNCTION public.pg_stat_statements_reset(userid oid, dbid oid, queryid bigint, minmax_only boolean) TO u2vbp82enb8hvq;


--
-- Name: extension_before_drop; Type: EVENT TRIGGER; Schema: -; Owner: heroku_admin
--

CREATE EVENT TRIGGER extension_before_drop ON ddl_command_start
   EXECUTE FUNCTION _heroku.extension_before_drop();


ALTER EVENT TRIGGER extension_before_drop OWNER TO heroku_admin;

--
-- Name: log_create_ext; Type: EVENT TRIGGER; Schema: -; Owner: heroku_admin
--

CREATE EVENT TRIGGER log_create_ext ON ddl_command_end
   EXECUTE FUNCTION _heroku.create_ext();


ALTER EVENT TRIGGER log_create_ext OWNER TO heroku_admin;

--
-- Name: log_drop_ext; Type: EVENT TRIGGER; Schema: -; Owner: heroku_admin
--

CREATE EVENT TRIGGER log_drop_ext ON sql_drop
   EXECUTE FUNCTION _heroku.drop_ext();


ALTER EVENT TRIGGER log_drop_ext OWNER TO heroku_admin;

--
-- Name: validate_extension; Type: EVENT TRIGGER; Schema: -; Owner: heroku_admin
--

CREATE EVENT TRIGGER validate_extension ON ddl_command_end
   EXECUTE FUNCTION _heroku.validate_extension();


ALTER EVENT TRIGGER validate_extension OWNER TO heroku_admin;

--
-- PostgreSQL database dump complete
--

\unrestrict M0IYe2XhPjm2XVrxDYLwOLxti4Gn3DMqdT7Hw8HbYO6K5eh7MqRAmnlq4IvdKyR

