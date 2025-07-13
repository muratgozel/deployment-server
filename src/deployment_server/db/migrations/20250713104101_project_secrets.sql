-- migrate:up
create type secrets_provider as enum ('LOCAL', 'COLDRUNE');

alter table project
add column secrets_provider secrets_provider;

-- migrate:down
