# Video Reverse Search

This is the repository for a fully functional app related to my blogpost: [Searching Videos From Screenshots](https://rorre.me/blog/post/searching-video)

## Running

GUI
```
uv run python -m video_search.gui.main
```

CLI
```
❯ python main.py --help               
                                                                                    
 Usage: main.py [OPTIONS] COMMAND [ARGS]...                                         
                                                                                    
╭─ Options ────────────────────────────────────────────────────────────────────────╮
│ --db-path                   PATH  Path to database [default: data.db]            │
│ --install-completion              Install completion for the current shell.      │
│ --show-completion                 Show completion for the current shell, to copy │
│                                   it or customize the installation.              │
│ --help                            Show this message and exit.                    │
╰──────────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────────╮
│ index                                                                            │
│ search                                                                           │
╰──────────────────────────────────────────────────────────────────────────────────╯

❯ python main.py index --help        
                                                                                    
 Usage: main.py index [OPTIONS] DIRECTORY                                           
                                                                                    
╭─ Arguments ──────────────────────────────────────────────────────────────────────╮
│ *    directory      PATH  Directory to scan for video files and index [required] │
╰──────────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────────╮
│ --recurse    --no-recurse      Run scan recursively [default: no-recurse]        │
│ --help                         Show this message and exit.                       │
╰──────────────────────────────────────────────────────────────────────────────────╯

❯ python main.py search --help       
                                                                                    
 Usage: main.py search [OPTIONS] IMAGE                                              
                                                                                    
╭─ Arguments ──────────────────────────────────────────────────────────────────────╮
│ *    image      PATH  Image file to find for the source [required]               │
╰──────────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────────╮
│ --threshold        FLOAT  Threshold for similarity [default: 0.8]                │
│ --help                    Show this message and exit.                            │
╰──────────────────────────────────────────────────────────────────────────────────╯
```
