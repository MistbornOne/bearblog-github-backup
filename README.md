# Bearblog GitHub Backup Tool 🔧

This little script was written out of a desire to backup my <a href="https://bearblog.dev" target="_blank">Bearblog</a> site.  The blogging platform is great, but the only built in way to back up your blog is very manual - so I made a way to utilize the RSS feed to do so.

## How Does It Work? 🚧

The Python script tells GitHub actions to check for an update every 6 hours.  If there has been a new update to your RSS feed, then GitHub will pull the HTML from your post and parse it into Markdown format and save it as a .md file on your repository in the "posts" folder (included in the repo).

You can change the chron job time to be whatever you'd like, but I initially set it at a 6 hour interval because I sometimes write multiple posts in one day.

Also, I built in logic to prevent duplicates by simply naming the file the `title-of-your-blog-post.md` and the script checks for an exact match for the de-dupe verification.

>[!NOTE]
>One thing to note is that the RSS feed is limited to 10 most recent posts, so you need to manually add any older posts by downloading them from the Settings section of your Bearblog dashboard (use the markdown option) and uploading them into the GitHub repository.

## How to Use 🧠

1. Clone or fork this repo -or- create your own repo for storing your backup
2. Go into the .github/workflows directory and remove the '#' from the front of line 5 (# - cron: "0 */6 * * *" # Runs every 6 hours after you remove the front comment hash) to ensure the workflow will run
3. Be sure that you go to the repo settings, then add a variable to actions (currently under secrets and variables)
  a. Name the variable: BEARBLOG_RSS_URL
  b. Make the content your RSS feed: https://YOURBLOG.com/feed/

That's it!  Now, you can manually trigger the workflow under actions to see if it works.  If not, GitHub will give you the specific error that caused it to fail.

---

💪🏼 Contribute

Feel free to open an issue or PR! Feature requests and bug reports are welcome.

---

📝 License

[MIT](https://github.com/MistbornOne/bearblog-github-backup/blob/main/LICENSE) © Ian Watkins
