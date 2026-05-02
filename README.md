# Bearblog GitHub Backup Tool 🔧

This little script was written out of a desire to backup my <a href="https://bearblog.dev" target="_blank">Bearblog</a> site.  The blogging platform is great, but the only built in way to back up your blog is very manual - so I made a way to utilize the RSS feed to do so.

## How to Use 🧠

1. Clone or fork this repo -or- create your own repo for storing your backup
2. Be sure that you go to the repo settings, then add a variable to actions (currently under secrets and variables)
  3. Name the variable: BEARBLOG_RSS_URL
  4. Make the content your RSS feed: https://YOURBLOG.com/feed/

That's it!  Now, you can manually trigger the workflow under actions to see if it works.  If not, GitHub will give you the specific error that caused it to fail.

---

💪🏼 Contribute

Feel free to open an issue or PR! Feature requests and bug reports are welcome.

---

📝 License

[MIT](https://github.com/MistbornOne/bearblog-github-backup/blob/main/LICENSE) © Ian Watkins
