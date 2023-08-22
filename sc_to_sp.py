import datetime
import json
import spotipy
from spotipy.oauth2 import SpotifyOAuth

def cleanse_ignorechars(string):
    ignorechars = ["(", ")", "/", "|", ".", "[", "]", "{", '}', '_', '-', ',', ':', '!', '&', "'"]
    for char in ignorechars:
        string = string.replace(char, "")
    return string

def match_score(str1, str2):
    str1_clean = cleanse_ignorechars(str1.lower())
    str2_clean = cleanse_ignorechars(str2.lower())

    s1 = set(str1_clean.split())
    s2 = set(str2_clean.split())
    matches = len(s1.intersection(s2))
    return 100 * (2 * matches) / (len(s1) + len(s2)), matches

def get_sp_result(sc_song, long_sc_song, indent=0):
    result = sp.search(sc_song, limit=1, type="track")
    if result is None:
        print(f"No results for {sc_song}")
        return None, None, None, None, None, None
    try:
        sp_uri = result["tracks"]["items"][0]["uri"]
        sp_title = result["tracks"]["items"][0]["name"]
        sp_artists = ", ".join([artist["name"] for artist in result["tracks"]["items"][0]["artists"]])
        sp_song = f"{sp_title} - {sp_artists}"
        sp_song_spaceless = f"{sp_title} - {sp_artists.replace(' ', '')}"

        # Compute score as % of words in both soundcloud sc_song and spotify sp_song
        score1, matches1 = match_score(sc_song, sp_song)
        score2, matches2 = match_score(sc_song, sp_song_spaceless)
        final_score = score1 if matches1 > matches2 else score2

        percent = f"({int(final_score)}%)"
        if final_score < 50:
            # red
            percent = "\033[91m" + percent + "\033[0m"
        elif final_score < 67:
            # amber
            percent = "\033[93m" + percent + "\033[0m"
        
        printable = " " * (indent) + f"{percent} {sc_song}\033[90m  ->  {sp_song}\033[0m"
        if long_sc_song == sc_song:
            long_printable = printable
        else:
            long_printable = " " * (indent) + f"{percent} {sc_song}\033[90m (originally: {long_sc_song})  ->  {sp_song}\033[0m"

        return printable, long_printable, sc_song, sp_song, sp_uri, final_score
    except IndexError:
        print(f"No results for {sc_song}")
        return None, None, None, None, None, None


##### SCRIPT #####
try:
    source_txt = input("Please provide a path to a text file containing your Soundcloud likes (default: 'soundcloud_paste.txt'):\n")
    if source_txt == "":
        source_txt = "soundcloud_paste.txt"

    # Read soundcloud_paste.txt
    soundcloud_paste = ""
    with open(source_txt, "r", encoding="utf-8") as f:
        soundcloud_paste = f.read()

    print(f"Read {len(soundcloud_paste)} characters from {source_txt}.")

    # Take all lines between "\n\n" and "Legal ?"
    songs = soundcloud_paste.split("\n\n")[1].split("Legal ⁃")[0]
    songs = songs.split("\n")

    # Remove any lines consisting of only ׉
    songs = [line for line in songs if line.strip() != "׉" and line.strip() != ""]
    songcount = len(songs)/2

    # Pair into title and artist
    songs = list(zip(songs[::2], songs[1::2]))
    print(f"Filtered down to {len(songs)} songs.")

    # Spotify developer credentials
    credentials = json.load(open("credentials.json", "r"))
    print(f"Loaded credentials for {credentials['username']}. Authenticating...")

    # Authenticating
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id=credentials["client_id"],
        client_secret=credentials["client_secret"],
        redirect_uri=credentials["redirect_uri"],
        scope="playlist-modify-public",
        username=credentials["username"]))
    print("Authenticated successfully!")

    # Creating a new playlist
    datenow = datetime.datetime.now()
    datenow_formatted = datenow.strftime("%H:%M %d/%m/%y")
    playlist = sp.user_playlist_create(user=credentials["username"], name=f"Soundcloud likes - x{songcount} - {datenow_formatted}")
    playlist_id = playlist["id"]

    # Search for each song on Spotify
    print(f"\n\nFinding matches for {len(songs)} songs (ETA {round((35/60) * len(songs)/100, 1)} minutes):")
    uris, ambiguities, failures = [], [], []
    i = 1
    for sc_title, sc_artist in songs:
        attempts = []

        sc_song = f"{sc_title} - {sc_artist}"
        song_reduced = cleanse_ignorechars(" ".join([word for word in sc_song.split() if "." not in word])).replace("Official", "")
        
        printable, long_printable, sc_song, sp_song, sp_uri, final_score = get_sp_result(sc_song, sc_song)
        print(f"[{i}/{len(songs)}] {printable}")
        attempts.append((sp_uri, final_score, printable, long_printable))

        if final_score is None or final_score < 67:
            printable, long_printable, sc_song, sp_song, sp_uri, final_score = get_sp_result(sc_title, sc_song, 2)
            print(printable)
            attempts.append((sp_uri, final_score, printable, long_printable))

            printable, long_printable, sc_song, sp_song, sp_uri, final_score = get_sp_result(song_reduced, sc_song, 2)
            print(printable)
            attempts.append((sp_uri, final_score, printable, long_printable))

        # Remove any None entries from attempts
        attempts = [attempt for attempt in attempts if attempt[0] is not None]
        best_attempt = max(attempts, key=lambda x: x[1])

        if best_attempt[1] >= 67:
            uris.append(best_attempt[0])
        elif best_attempt[1] >= 1:
            ambiguities.append(best_attempt)
        else:
            failures.append(best_attempt)
        i+=1

    # Manually resolve ambiguities
    print(f"\n{len(uris)} songs found, {len(failures)} not found, {len(ambiguities)} songs ambiguous:\n")
    i = 0
    for amb_uri, amb_match, amb_print, amb_long_print in ambiguities:
        i += 1
        print(f"{str(i)}/{len(ambiguities)}:" + amb_long_print)
        ans = ""
        while ans.lower() not in ["y", "n", "yall", "nall"]:
            ans = input("Add this song? (y/n/yall/nall) ")
        if ans.lower() == "y":
            uris.append(amb_uri)
        elif ans.lower() == "n":
            failures.append((amb_uri, amb_match, amb_print, amb_long_print))
        elif ans.lower() == "yall":
            uris.append(amb_uri)
            for amb_uri, amb_match, amb_print, amb_long_print in ambiguities[i:]:
                uris.append(amb_uri)
            break
        elif ans.lower() == "nall":
            failures.append((amb_uri, amb_match, amb_print, amb_long_print))
            for amb_uri, amb_match, amb_print, amb_long_print in ambiguities[i:]:
                failures.append((amb_uri, amb_match, amb_print, amb_long_print))
            break

    # Inform of failures
    print(f"\n{len(uris)} songs found, {len(failures)} songs not found:\n")
    for fail_uri, fail_match, fail_print, fail_long_print in failures:
        print(fail_long_print)

    # Adding songs to the playlist, 100 at a time
    for i in range(0, len(uris), 100):
        sp.user_playlist_add_tracks(user=credentials['username'], playlist_id=playlist_id, tracks=uris[i:i+100])

    # Account for leftover songs
    if len(uris) % 100 != 0:
        sp.user_playlist_add_tracks(user=credentials['username'], playlist_id=playlist_id, tracks=uris[len(uris) - (len(uris) % 100):])

    print(f"Playlist of {len(uris)} songs created successfully, at https://open.spotify.com/playlist/{playlist_id}")
except Exception as e:
    print(f"An error occurred: {e}")

input("Press enter to exit.")