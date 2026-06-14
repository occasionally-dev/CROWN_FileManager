# CROWN_FileManager
CROWN_FileManager — Remote File Access via Telegram

FEATURES:

    Telegram bot control — browse, download, delete any files
    
    Multiple admins — access from several Telegram accounts
    
    Self-installing — downloads portable Python, installs dependencies, adds to startup
    
    No console window — completely hidden operation
    
    Cross-platform — Windows & Linux (Linux version with systemd/crontab)

Bot Commands:

                 Command	| Action
             
                  /start	| Show main menu with drives/folders
              
            Click on folder |	Open directory
      
              Click on file |	Download file
        
           Delete button	| Remove file/folder
       
    Self-destruct button	| Completely remove the program from PC   

Setup (For Your Control Panel)

    Create bot via @BotFather → get BOT_TOKEN
    
    Get your Telegram ID: @userinfobot
    
    Edit config section in the script:
    python
"
    BOT_TOKEN = "your_token_here"
    ADMIN_IDS = [123456789, 987654321]  # your Telegram IDs
                                                                "

    Run the script

  ⚠️ Disclaimer:
    This tool is for educational purposes only. Use only on systems you own or have explicit permission to test. Unauthorized access is illegal.
