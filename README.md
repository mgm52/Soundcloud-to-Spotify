# Soundcloud-to-Spotify
A command-line executable to convert Soundcloud likes into Spotify playlists.

### Usage
- Create a file called `credentials.json` in the same directory as the executable, and fill it out with details of your Spotify API access:
```
{
    "username": "...",
    "client_id": "...",
    "client_secret": "...",
    "redirect_uri": "..."
}
```
- Copy the content of https://soundcloud.com/you/likes (simply `CTRL+A`, `CTRL+C` on Windows) into a text file. (Unfortunately Soundcloud doesn't offer a nicer API for this...)
- Run `sc_to_sp.exe` and provide the path to the text file.
