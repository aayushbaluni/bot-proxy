module.exports = {
  apps: [
    {
      name: 'proxy-bot-sequential-10min',
      script: 'main.py',
      args: '--sequential --cycle-interval 10',
      interpreter: 'python3',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '1G',
      env: {
        NODE_ENV: 'production'
      },
      error_file: './logs/proxy-sequential-error.log',
      out_file: './logs/proxy-sequential-out.log',
      log_file: './logs/proxy-sequential-combined.log',
      time: true,
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
      merge_logs: true,
      kill_timeout: 5000,
      restart_delay: 5000
    },
    {
      name: 'proxy-bot-sequential-5min',
      script: 'main.py',
      args: '--sequential --cycle-interval 5',
      interpreter: 'python3',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '1G',
      env: {
        NODE_ENV: 'production'
      },
      error_file: './logs/proxy-sequential-5min-error.log',
      out_file: './logs/proxy-sequential-5min-out.log',
      log_file: './logs/proxy-sequential-5min-combined.log',
      time: true,
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
      merge_logs: true,
      kill_timeout: 5000,
      restart_delay: 5000
    },
    {
      name: 'proxy-bot-auto',
      script: 'main.py',
      args: '--auto --fetch-interval 60 --test-interval 30',
      interpreter: 'python3',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '1G',
      env: {
        NODE_ENV: 'production'
      },
      error_file: './logs/proxy-bot-error.log',
      out_file: './logs/proxy-bot-out.log',
      log_file: './logs/proxy-bot-combined.log',
      time: true,
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
      merge_logs: true,
      kill_timeout: 5000,
      restart_delay: 5000
    }
  ]
};