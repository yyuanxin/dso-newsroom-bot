# dso-newsroom-bot
Bot that checks for new releases. For AWS Lambda Function

Used by a telegram bot that updates the telegram channel on the new releases.

### Sites that the bot currently tracks for new releases
- Burpsuite
- Gitlab
- AWS CLI
- Corretto 11
- Corretto 17
- Maven
- Nodejs (14/18/20)
- Sonarqube
- Dependency Check

### Content
```
 ├── Notes.md // FYI notes about the bot
 ├── cached.txt // Stores cached data of the latest releases. Bot will read/write to this file
 ├── classes.py // Code implementation here
 ├── lambda_function.py // Main function. Update site URLs here.
 ├── script.sh // Prep script to update lambda function. Run this locally and upload output file to lambda.
 └── requirements.txt // list of python packages required
```

## Create s3 bucket to store cached data
Used to store cached data of the latest releases. (Currently used for gitlab only)
Use Case: For sites with no timestamps. Eg: `2023-02-14T00:00:00+00:00`

1. Create a s3 bucket `rss-code`
2. Update cached.txt with the latest data
3. Upload cached.txt to `rss-code` bucket

## Deploy to Lambda

1. Create a python3.9 lambda function
2. Run `script.sh` locally and upload output file `python-package.zip`
3. Create 3 environment variables
   - Key: BOT_TOKEN
     Value: <telegram-bot-token>
   - Key: CHANNEL_ID
     Value: <telegram-channel-id>
   - Key: HOURS
     Value: <how-often-bot-checks-for-new-releases>

## Set Daily cron job with EventBridge

1. Create new recurring schedule (rate-based)
2. Set rate expression to match with `HOURS` environment variable set in Lambda
