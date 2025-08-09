-- migrate:up
alter type deployment_status add value 'SKIPPED' after 'SUCCESS';

-- migrate:down
