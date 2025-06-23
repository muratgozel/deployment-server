-- migrate:up
create table project (
    rid text not null constraint project_pk primary key,
    created_at timestamp with time zone default now(),
    updated_at timestamp with time zone,
    removed_at timestamp with time zone,
    name text not null,
    code text not null,
    git_url text,
    pip_package_name text,
    pip_index_url text,
    pip_index_user text,
    pip_index_auth text
);


create type daemon_type as enum ('SYSTEMD', 'DOCKER');

create table daemon (
    rid text not null constraint daemon_pk primary key,
    created_at timestamp with time zone default now(),
    updated_at timestamp with time zone,
    removed_at timestamp with time zone,
    type daemon_type,
    project_rid text references project (rid) on delete cascade,
    name text not null,
    port int default 0,
    py_module_name text
);


create table deployment (
    rid text not null constraint deployment_pk primary key,
    created_at timestamp with time zone default now(),
    updated_at timestamp with time zone,
    removed_at timestamp with time zone,
    project_rid text references project (rid) on delete cascade,
    version text not null,
    mode text,
    scheduled_to_run_at timestamp with time zone
);


create type deployment_status as enum ('SCHEDULED', 'READY', 'RUNNING', 'FAILED', 'SUCCESS');
-- to add more values later:
-- alter type deployment_status add value 'orange' after 'failed';

create table deployment_status_update (
    rid text not null constraint deployment_status_update_pk primary key,
    created_at timestamp with time zone default now(),
    updated_at timestamp with time zone,
    removed_at timestamp with time zone,
    deployment_rid text references deployment (rid) on delete cascade,
    status deployment_status,
    description text
);

-- create index deployment_status_update_created_at_index
--     on deployment_status_update (created_at desc);

-- migrate:down
