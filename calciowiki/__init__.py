import mwparserfromhell
import urllib.request
import urllib.parse
import re
import parsedatetime
import dateutil
import datetime
import time as timelib
import json
import string
import os
from PIL import Image
import logging
import pandas as pd
import numpy as np
from dateutil.parser import parse
from io import BytesIO
import requests
import arrow

class WikiPage(object):
    #competition_text = {"Serie A" : "Ser A", "Champions League" : "UCL", "Europa League" : "EL", "Coppa Italia": "CI", "Friendly": "Fr"}
    _api_url = "https://en.wikipedia.org/w/api.php"
    _api_url_en = "https://en.wikipedia.org/w/api.php"
    _api_url_it = "https://it.wikipedia.org/w/api.php"

    def __init__(self, title, lang='en'):
        self.title = title
        self.lang = lang
        if lang == 'it':
            self._api_url = self._api_url_it 
        else:
            self._api_url = self._api_url_en
        self.wikicode = self._get_page()

    def _get_page(self):

        logging.debug(f"Getting Page: {self.title}")
        data = {"action": "query", "prop": "info|revisions", "inprop":"url", "rvlimit": 1,"rvprop": "content", "format": "json", "titles": self.title,"redirects":1}
        response = urllib.request.urlopen(self._api_url, urllib.parse.urlencode(data).encode()).read()
        jsonresponse = json.loads(response.decode("utf-8"))
        self.url = list(jsonresponse["query"]["pages"].values())[0]["fullurl"]
        try:
            return mwparserfromhell.parse(list(jsonresponse["query"]["pages"].values())[0]["revisions"][0]['*'],skip_style_tags=True)
        except:
            return None

    def _get_text(self,wikicode):
        return wikicode.strip_code().strip()

    def _get_timestamp (self, date, time=None):
        date = self._get_text(date)
        if time is not None:
            time = self._get_text(time)
            if time[:5] == "--:--":
                time = None
        dt = timelib.mktime(timelib.strptime('24/05/2030', "%d/%m/%Y"))
        if time is not None:
            date = date + ' ' + re.sub(r'\([^)]*\)', '', time)
        try:
            time_struct = parse(date)
            dt = datetime.datetime.timestamp(time_struct)
            return dt
        except:
            return None
        if datetime.date.fromtimestamp(dt).year == 2030:
            return None

    def _merge_date_time (self, date, time):
        dt = datetime.datetime.fromtimestamp(self._get_timestamp(date,time))
        return dt

class WikiPicture(WikiPage):
    def __init__(self, image_title,height=64,width=64):
        try:
            logging.info(f"Getting Image {image_title}")
            data = {"action": "query", "prop": "imageinfo","iiprop": "url", "format": "json", "iiurlheight": height, "iiurlwidth": width, "titles": image_title}
            response = urllib.request.urlopen(self._api_url, urllib.parse.urlencode(data).encode()).read()
            jsonresponse = json.loads(response.decode("utf-8"))
            image_url = list(jsonresponse["query"]["pages"].values())[0]["imageinfo"][0]["thumburl"]
            image_response = requests.get(image_url)
            dl_image = Image.open(BytesIO(image_response.content))
            new_image = Image.new("RGBA", (width,height))
            x, y = dl_image.size
            x1 = int(width/2 - x/2)
            y1 = int(height/2 - y/2)
            new_image.paste(dl_image, (x1,y1))
            self._image = new_image
        except:
            self._image = None

    def get_image(self):
        return self._image

class WikiImage(WikiPage):
    def __init__(self, image_title, image_name, folder, color_mode="RGBA", height=64,width=64, temp_folder=os.path.join(os.sep,"usr","share","calciodb","tmp")):
        filename = image_name.lower().replace(" ","_")

        if not os.path.exists(temp_folder):
            os.makedirs(temp_folder)

        for f in os.listdir(temp_folder):
            os.remove(os.path.join(temp_folder,f))
            logging.debug (f)

        image_full_path = os.path.join(folder, filename + ".png")
        logging.debug(image_full_path)
        if not os.path.exists(image_full_path):
            logging.debug(f"Getting file: {filename}")
            data = {"action": "query", "prop": "imageinfo","iiprop": "url", "format": "json", "iiurlheight": height, "iiurlwidth": width, "titles": image_title}
            response = urllib.request.urlopen(self._api_url, urllib.parse.urlencode(data).encode()).read()
            jsonresponse = json.loads(response.decode("utf-8"))

            image_url = list(jsonresponse["query"]["pages"].values())[0]["imageinfo"][0]["thumburl"]
            temp_image = os.path.join(os.path.dirname(os.path.realpath(__file__)), temp_folder , os.path.basename(image_url))
            urllib.request.urlretrieve(image_url,temp_image)

            tempImage = Image.open(temp_image)
            newImage = Image.new(color_mode, (width,height))
            x, y = tempImage.size
            x1 = int(width/2 - x/2)
            y1 = int(height/2 - y/2)
            newImage.paste(tempImage, (x1,y1))
            tempImage.close()

            newImage.save(image_full_path)
            os.remove(temp_image)
        else:
            logging.debug("%s Exists." % filename)
        self.image_path = os.path.join(folder, filename + ".png")

class WikiPlayer(WikiPage):
    def __init__(self, player_name):
        self.name = player_name
        super(WikiPlayer,self).__init__(player_name)
        self.player_details = self._parse()

    def _parse(self):
        wikicode = self.wikicode
        page_url = self.url
        juve_wikicode = None
        s = str(wikicode.get_sections(flat=True).pop(0))
        for section in wikicode.get_sections(flat=True):
            for heading in section.filter_headings():
                if "Juventus" in heading:
                    s = s + '## '+str(section)

        p = re.compile( '(<ref(.*?)<\/ref>)+')
        s = p.sub('',s)
        s = mwparserfromhell.parse(s)
        s = s.strip_code()

        p = re.compile( '(\(; )+')
        s = p.sub('(',s)

        s = mwparserfromhell.parse(s)
        s = s.strip_code()

        p = re.compile( '(\(\))+')
        s = p.sub('',s)

        s = re.sub( r'===(.*)===',r'\n\n## \1 \n\n',s)

        s = s + "\n\nRead more about " + self.name + " [here]("+page_url+")!"

        title = "#" + self.name + "\n"

        for template in wikicode.filter_templates():
            if "Infobox football biography" in template.name:
                i = 1
                team = []
                dob = ""
                dod = None
                other_clubs = ""
                for x in mwparserfromhell.wikicode.parse_anything(template.get("birth_date").value).filter_templates():
                    if "birth date" in x.name:
                        dob = "%s/%s/%s" % (x.get(3),x.get(2),x.get(1))

                if template.has("death_date"):
                    for x in mwparserfromhell.wikicode.parse_anything(template.get("death_date").value).filter_templates():
                        dod = "%s/%s/%s" % (x.get(3),x.get(2),x.get(1))

                while template.has("clubs" + str(i)):
                    if "Juventus" in template.get("clubs" + str(i)).value.strip_code():
                        team.append({"id":i,"team":template.get("clubs" + str(i)).value.strip_code(), "appearances":int(template.get("caps" + str(i)).value.strip_code()), "goals": int(template.get("goals" + str(i)).value.strip_code()), "years": template.get("years" + str(i)).value.strip_code()})
                    else:
                        other_clubs += (template.get("clubs" + str(i)).value.strip_code().strip()) + ", "
                    i += 1

                other_clubs = other_clubs[:-2]
                other_clubs = " and".join(other_clubs.rsplit(",", 1))
                total_app = 0
                total_goals = 0
                years = ""
                for t in team:
                    total_app += t["appearances"]
                    total_goals += t["goals"]
                    years += str(t["years"]).strip()
                    if (len(team) > 1):
                        years += " ("+ str(t["appearances"])+")"
                    years += ", "

                years = years[:-2]
                profile = "| Profile     | |\n|------------:|:--|\n| Name        | " + self.name + " |\n" + \
                          "| Position    | " + template.get("position").value.strip_code().strip() + " |\n" +\
                          "| DoB         | " + dob + " |\n"
                if template.has("death_date") and dod is not None:
                    profile += "| Death       | " + dod + " |\n"

                profile +="| Club Stints | " + years + " |\n" + \
                          "| Total Caps  | " + str(total_app)+ " |\n" + \
                          "| Total Goals | " + str(total_goals)+ " |\n" + \
                          "| Other Clubs | " + other_clubs + " |\n\n"

                im = "File:" + template.get("image").value.strip()

                logging.debug (f"Using image: {im}")
                if im[-4] == ".":
                    wiki_image = WikiImage(im, self.name, os.path.join(os.sep,"usr","share","calciodb","potm-images"), "LA")
                    wiki_large_image = WikiImage(im, self.name, os.path.join(os.sep,"usr","share","calciodb","potm-large-images"), height=512,width=512)
                    self.image_path = wiki_image.image_path
                    self.large_image_path = wiki_large_image.image_path
                else:
                    self.image_path = None
                self.appearances = total_app
                return {"content": title + profile + "##Bio\n\n" + s, "title":"[Player of the Month] " +  self.name + " (" + str(total_app)+" appearances)",'name': self.name, 'caps':total_app, 'image_name': im, 'years': years, 'appearances':total_app, 'large_image':self.large_image_path, 'small_image':self.image_path,'wikipedia':page_url }
        return {"content": title + "##Bio\n\n" + s, "title":"[Player of the Month] " +  self.name,'name': self.name, 'caps': 0}

class WikiSeason(WikiPage):
    def __init__(self, title):
        super(WikiSeason,self).__init__(title.replace('-','–'))
        self.title = title
        years = title.split()[0].replace('–','-').split('-')
        self.year = f"{years[0][-2:]}-{years[1][-2:]}"
        self.season = self._parse()

    def _parse(self):
        matches = pd.DataFrame()
        events = pd.DataFrame()
        tables = pd.DataFrame()
        club = ""
        for template in self.wikicode.filter_templates():
            if template.name.matches("Infobox football club season"):
                club = self._get_text(template.get("club").value)

        logging.debug ("Processing season for club: %s." % club)

        for template in self.wikicode.filter_templates():
            if template.name.matches("footballbox collapsible") or template.name.matches("football box collapsible"):
                previous_headings = []
                found = False
                for section in self.wikicode.get_sections(levels=[3]):
                    if section.contains(template):
                        previous_headings = [heading for heading in section.filter_headings()]
                        found=True
                comp = previous_headings[0].title.strip_code().strip() if found else "Friendly"

                team1_full = self._get_text(template.get("team1").value)
                for l in template.get("team1").value.filter_wikilinks():
                    team1_full = l.title

                team2_full = self._get_text(template.get("team2").value)
                for l in template.get("team2").value.filter_wikilinks():
                    team2_full = l.title

                ref_name = "N/A"
                try:
                    ref_name = re.sub(r'\([^)]*\)', '', self._get_text(template.get("referee").value)).strip()
                except:
                    pass
                time = self._get_timestamp(template.get("date").value, template.get("time").value) if template.has("time") else self._get_timestamp(template.get("date").value)
                r = {
                        'season': self.year,
                        'home_team' : self._get_text(template.get("team1").value),
                        'home_full_name': str(team1_full),
                        'away_team' : self._get_text(template.get("team2").value),
                        'away_full_name':str(team2_full),
                        'referee' : ref_name,
                        'time' : time,
                        'competition': comp
                    }
                # print(r)
                if time is None:
                    logging.info(f"Match dropped - {r['season']} {r['competition']}: {r['home_team']} - {r['away_team']}")
                    continue
                stadium_name = "N/A"
                try:
                    stadium_name = self._get_text(template.get("stadium").value).strip()
                except:
                    pass
                stadium = stadium_name
                goals = self._get_text(template.get("score").value).replace(u'\u2013','-').split('-')

                r['home_goals'] = goals[0] if len(goals) == 2 else ""
                r['away_goals'] = goals[1] if len(goals) == 2 else ""
                r['result'] = self._get_text(template.get("result").value)
                r['h_a'] = 'H' if r['home_team'] == club else 'A'

                # GET ATTENDANCE
                if template.has("attendance"):
                    attendance = self._get_text(template.get("attendance").value).replace(',','') #remove thousands comma
                    r['attendance'] = attendance if attendance != "" and attendance.isdigit() else "0"

                # GET LOCATION
                if template.has("location"):
                    location = self._get_text(template.get("location").value)
                    if len(location) < 64:
                        location = stadium + ', ' + location if len(stadium) > 0 else location
                    else:
                        location = stadium
                else:
                    location = stadium
                r['location'] = location

                # GET COMPETITION

                # if template.has("round"):
                #     comp = template.get("round").value
                #
                #     comp_title = self._get_text(comp)
                #     r['competition'] =  comp_title if len(comp_title.split()) == 1 else ".".join( [ w[0] for w in comp_title.split() ] )
                #
                #     if comp.strip_code().strip().isdigit():
                #         r['competition'] = "Ser A"
                #     if "Champions League" in comp:
                #         r['competition'] = "UCL"
                #     if "Europa League" in comp:
                #         r['competition'] = "EL"
                #     if "Coppa Italia" in comp:
                #         r['competition'] = "CI"
                #     if "Friendly" in comp:
                #         r['competition'] = "Fr"
                if len(r['home_team']) > 1 or len(r['away_team']) > 1:
                    linebreaks = ["<br>","<br/>","<br />","*"]
                    goals = ['goals1','goals2']
                    for goal_set in goals:
                        if template.has(goal_set):
                            goal_list = re.split(r"(<br>)|(<br/>)|(<br />)|(\*)",str(template.get(goal_set).value))
                            for linebreak in linebreaks:
                                if linebreak in goal_list:
                                    goal_list.remove(linebreak)
                            if None in goal_list:
                                goal_list.remove(None)
                            home_or_away = 'home_team' if goal_set == goals[0] else 'away_team'
                            events = pd.concat([events, self._get_events_dict(goal_list,r,r[home_or_away])])
                    matches = pd.concat([matches,pd.DataFrame([r])],sort=True)

            elif ("Serie A" in template.name):
                # or ("Champions League" in template.name) or ("Europa League" in template.name):
                try:
                    wt = WikiTable(str(template.name))
                    tables = pd.concat( [tables, wt.tables ] )
                except:
                    logging.debug("No valid table.")
        logging.debug(matches)
        if "time" in matches.columns:
            matches.sort_values(by="time", inplace=True)

        return {'club':club, 'matches':matches, 'events':events, 'tables': tables}

    def _get_events_dict(self, team_events, r, team): # team_events as List
        events_list = []
        match_time = r['time']
        for i,event in enumerate(team_events):
            player_name = self._get_text(mwparserfromhell.wikicode.parse_anything(event))
            player_name = ''.join(ch for ch in player_name if ch not in set(string.punctuation)).strip()

            for t in mwparserfromhell.wikicode.parse_anything(event).filter_templates():
                if t.name.lower() == "goal" or t.name == "yel":
                    for i in range(0, len(t.params), 2):
                        event_desc = t.params[i+1] if len(t.params) > i+1 else ""
                        event_time = t.params[i].split('+')[0].strip()
                        if event_time.isdigit():
                            events_list.append({'time' : event_time, 'player': player_name, 'type': str(t.name).lower(), 'desc' : event_desc, 'match_time':match_time, 'team': team, 'season':r['season']})
                elif t.name == "sent off":
                    event_desc = "strt" if t.params[0] == '0' else "dbly"
                    event_time = t.params[1].strip()
                    if event_time.isdigit():
                        events_list.append({'time' : event_time, 'player': player_name,'type': str(t.name), 'desc' : str(event_desc), 'match_time':match_time, 'team': team, 'season':r['season']})
        return pd.DataFrame(events_list)

class WikiSeasonIt(WikiPage):
    def __init__(self, title):
        super(WikiSeasonIt,self).__init__(title=title,lang='it')
        self.title = title
        years = [wd for wd in title.split(' ') if '-' in wd][0].split('-')
        self.year = f"{years[0][-2:]}-{years[1][-2:]}"
        self.season = self._parse()

    def _parse(self):
        matches = pd.DataFrame()
        events = pd.DataFrame()
        tables = pd.DataFrame()
        club = ""
        for template in self.wikicode.filter_templates():
            if template.name.matches("Stagione squadra"):
                club = self._get_text(template.get("club").value)

        logging.debug ("Processing season for club: %s." % club)

        for template in self.wikicode.filter_templates():
            if template.name.matches("Incontro di club") or template.name.matches("incontro di club"):
                previous_headings = []
                found = False
                for section in self.wikicode.get_sections(levels=[3]):
                    if section.contains(template):
                        previous_headings = [heading for heading in section.filter_headings()]
                        found=True
                comp = previous_headings[0].title.strip_code().strip() if found else "Friendly"

                team1_full = self._get_text(template.get("Squadra 1").value)
                for l in template.get("Squadra 1").value.filter_wikilinks():
                    team1_full = l.title

                team2_full = self._get_text(template.get("Squadra 2").value)
                for l in template.get("Squadra 2").value.filter_wikilinks():
                    team2_full = l.title

                ref_name = "N/A"
                try:
                    ref_name = re.sub(r'\([^)]*\)', '', self._get_text(template.get("Arbitro").value)).strip()
                except:
                    pass
                # time = self._get_timestamp(template.get("date").value, template.get("time").value) if template.has("time") else self._get_timestamp(template.get("date").value)
                date = f'{str(template.get("Giornomese").value).strip()} {str(template.get("Anno").value).strip()}' 
                date = self._date_to_en(date)
                time = self._get_text(template.get("Ora").value).strip()
                if ':' not in time:
                    time = "00:00" + time
                tzmapping = {'CET': dateutil.tz.gettz('Europe/Berlin'),
                            'CEST': dateutil.tz.gettz('Europe/Berlin')}

                match_dt = dateutil.parser.parse(f'{date} {time}', tzinfos=tzmapping)
                match_time = match_dt.timestamp()

                r = {
                        'season': self.year,
                        'home_team' : self._get_text(template.get("Squadra 1").value),
                        'home_full_name': str(team1_full),
                        'away_team' : self._get_text(template.get("Squadra 2").value),
                        'away_full_name':str(team2_full),
                        'referee' : ref_name,
                        'time' : match_time,
                        'competition': comp
                    }
                # print(r)
                if time is None:
                    logging.info(f"Match dropped - {r['season']} {r['competition']}: {r['home_team']} - {r['away_team']}")
                    continue
                stadium_name = "N/A"
                try:
                    stadium_name = self._get_text(template.get("Stadio").value).strip()
                except:
                    pass
                stadium = stadium_name
                goals = str(template.get("Punteggio 1").value) + ' - ' + str(template.get("Punteggio 2").value)

                r['home_goals'] = template.get("Punteggio 1").value.strip()
                r['away_goals'] = template.get("Punteggio 2").value.strip()
                r['h_a'] = 'H' if r['home_team'] in club else 'A'
                r['result'] = 'D'
                if r['home_goals'] > r['away_goals']:
                    r['result'] = 'W' if r['h_a'] == 'H' else 'L'
                elif r['home_goals'] < r['away_goals']:
                    r['result'] = 'L' if r['h_a'] == 'H' else 'W'
                
                r['attendance'] = ""
                # GET ATTENDANCE
                if template.has("Spettatori") and 'formatnum' in template.get("Spettatori").value:
                    af = template.get("Spettatori").value
                    at = 'formatnum:'
                    attendance = af[af.find(at)+len(at): af.find('}}')]
                    r['attendance'] = attendance if attendance != "" and attendance.isdigit() else ""

                # GET LOCATION
                if template.has("Città"):
                    location = self._get_text(template.get("Città").value)
                    if len(location) < 64:
                        location = stadium + ', ' + location if len(stadium) > 0 else location
                    else:
                        location = stadium
                else:
                    location = stadium
                r['location'] = location

                # GET COMPETITION

                # if template.has("round"):
                #     comp = template.get("round").value
                #
                #     comp_title = self._get_text(comp)
                #     r['competition'] =  comp_title if len(comp_title.split()) == 1 else ".".join( [ w[0] for w in comp_title.split() ] )
                #
                #     if comp.strip_code().strip().isdigit():
                #         r['competition'] = "Ser A"
                #     if "Champions League" in comp:
                #         r['competition'] = "UCL"
                #     if "Europa League" in comp:
                #         r['competition'] = "EL"
                #     if "Coppa Italia" in comp:
                #         r['competition'] = "CI"
                #     if "Friendly" in comp:
                #         r['competition'] = "Fr"
                if len(r['home_team']) > 1 or len(r['away_team']) > 1:
                    linebreaks = ["<br>","<br/>","<br />","*"]
                    goals = ['Marcatori 1','Marcatori 2']
                    for goal_set in goals:
                        if template.has(goal_set):
                            goal_list = re.split(r"(<br>)|(<br/>)|(<br />)|(\*)",str(template.get(goal_set).value))
                            for linebreak in linebreaks:
                                if linebreak in goal_list:
                                    goal_list.remove(linebreak)
                            if None in goal_list:
                                goal_list.remove(None)
                            home_or_away = 'home_team' if goal_set == goals[0] else 'away_team'
                            events = pd.concat([events, self._get_events_dict(goal_list,r,r[home_or_away])])
                    matches = pd.concat([matches,pd.DataFrame([r])],sort=True)

            elif ("Serie A" in template.name):
                # or ("Champions League" in template.name) or ("Europa League" in template.name):
                try:
                    wt = WikiTable(str(template.name))
                    tables = pd.concat( [tables, wt.tables ] )
                except:
                    logging.debug("No valid table.")
        # logging.debug(matches)
        if "time" in matches.columns:
            matches.sort_values(by="time", inplace=True)

        return {'club':club, 'matches':matches, 'events':events, 'tables': tables}

    def _date_to_en(self, date_it):
        mesi = ['gennaio','febbraio','marzo','aprile','maggio','giunio','luglio','agosto','settembre','ottobre','novembre','dicembre']
        parts = date_it.split()
        for i in range(0,len(parts)):
            if parts[i] in mesi:
                parts[i] = str(mesi.index(parts[i])+1)
            if parts[i].isdigit():
                parts[i] = parts[i].zfill(2)
            else:
                num = ''
                for l in parts[i]:
                    num += l if l.isdigit() else ''
                parts[i] = num.zfill(2)
        return '/'.join(parts)

    def _get_events_dict(self, team_events, r, team): # team_events as List
        events_list = []
        match_time = r['time']
        for i,event in enumerate(team_events):
            player_name = self._get_text(mwparserfromhell.wikicode.parse_anything(event))
            player_name = ''.join(ch for ch in player_name if ch not in set(string.punctuation)).strip()

            for t in mwparserfromhell.wikicode.parse_anything(event).filter_templates():
                if t.name.lower() == "goal" or t.name == "yel":
                    for i in range(0, len(t.params), 2):
                        event_desc = str(t.params[i+1]) if len(t.params) > i+1 else ""
                        event_dict = {'rig':'pen','aut':'og'}
                        event_desc_en = event_dict[event_desc] if event_desc in event_dict else ""
                        event_time = t.params[i].split('+')[0].strip()
                        if event_time.isdigit():
                            events_list.append({'time' : event_time, 'player': player_name, 'type': str(t.name).lower(), 'desc' : event_desc_en, 'match_time':match_time, 'team': team, 'season':r['season']})
                elif t.name == "sent off":
                    event_desc = "strt" if t.params[0] == '0' else "dbly"
                    event_time = t.params[1].strip()
                    if event_time.isdigit():
                        events_list.append({'time' : event_time, 'player': player_name,'type': str(t.name), 'desc' : str(event_desc), 'match_time':match_time, 'team': team, 'season':r['season']})
        return pd.DataFrame(events_list)

class WikiClassifica(WikiPage):
    def __init__(self, title):
        super(WikiClassifica, self).__init__(title,lang='it')
        self.title = title
        self.classifica = self._parse_classifica()

    def _table_to_html(self, t):
        # if isinstance(t,str):
        #   print(t.contents)
        #   return t
        attrs = " ".join([f'{a.name}="{a.value}"' for a in t.attributes])
        if len(t.attributes) > 0:
            attrs = " " + attrs
        m = f'<{t.tag}{attrs}>'
        if t.tag == 'table':
            m+= '<thead>'
        
        for c in t.contents.filter(recursive=False):
            if isinstance(c, mwparserfromhell.nodes.tag.Tag):
                m += self._table_to_html(c)
            elif isinstance(c,mwparserfromhell.nodes.text.Text):
                # m += c.value
                txt = mwparserfromhell.parse(c).strip_code().replace("'''","")
                if txt == 'Squadra':
                    txt = 'Team'
                m += txt
                pass
            elif isinstance(c,mwparserfromhell.nodes.template.Template):
                # m += str(mwparserfromhell.parse(c))
                if c.name.startswith('Calcio femminile'):
                    m += c.name[17:].strip()
                    break
                elif c.name.startswith('Calcio'):
                    m += c.name[7:].strip()
                    break      
                elif c.name.lower() == 'simbolo':
                    pass
                elif c.name.lower() == 'abbr':
                    abbrs = {'pos.':'Position','pt':'Points','g':'Played','v':'Won','n':'Draw','p':'Lost','gf':'Goals Scored','gs':'Goals Against','dr':'Goal Difference'}
                    if c.params[0].lower() in abbrs:
                        m += abbrs[c.params[0].lower()]
                    else:
                        m += c.params[-1] 
            elif isinstance(c,mwparserfromhell.nodes.html_entity.HTMLEntity):
                m += c.normalize()
            else:
                print(type(c))
        m += f'</{t.closing_tag}>'
        return m
    
    def _parse_classifica(self):
        y = mwparserfromhell.parse(self.wikicode)
        tables = []
        for s in y.get_sections(flat=True):
            if s[:s.find("\n")].lower().replace("=","").strip() == "classifica":
                for c in s.filter_tags():
                    if c.tag == 'table':
                        tbl = self._table_to_html(c)
                        ins = tbl.find("</th><tr")
                        tbl = tbl[:ins+5] + "</thead>" + tbl[ins+5:]
                        if 'Juventus' in tbl:
                            df = pd.read_html(tbl)
                            df = df[0].drop(['Unnamed: 0'], axis=1)
                            df['Position'] = df['Position'].astype(int)
                            return df
        return None

class WikiTable(WikiPage):
    def __init__(self, title):
        super(WikiTable, self).__init__('Template:' + title)
        self.title = 'Template:' + title
        self.tables = self._parse_table()

    def _parse_table(self):
        i = 1
        j = True
        logging.info(self.title)
        table = []
        for template in self.wikicode.filter_templates():
            if "Sports table" in template.name:
                #table = []
                team_codes = []
                if template.has("team_order"):
                    team_codes = template.get("team_order")
                    team_codes = team_codes.split("=")[1].split("\n")[0].strip().split(",")
                    team_codes = [team_code.strip() for team_code in team_codes]
                else:
                    while template.has("team" + str(i)):
                        team_code = str(template.get("team" + str(i)).value).split()[0].strip()
                        team_codes.append(team_code)
                        i = i + 1

                for i in range(1,len(team_codes)+1):
                    team_code = team_codes[i-1]
                    team_wins = int(str(template.get("win_" + team_code).value).split()[0])
                    team_draws = int(str(template.get("draw_" + team_code).value).split()[0])
                    team_loss =  int(str(template.get("loss_" + team_code).value).split()[0])
                    team_gf = int(str(template.get("gf_" + team_code).value).split()[0])
                    team_ga = int(re.search(r'\d+', str(template.get("ga_" + team_code).value)).group())
                    team = {
                            'season': template.get("template_name").value.strip()[2:7].replace("–","-"),
                            'competition': template.get("template_name").value.strip()[8:-6],
                            'code' :team_code,
                            'name' : self._get_text(template.get("name_" + team_code).value).strip(),
                            'wins' : team_wins,
                            'draws' :team_draws ,
                            'loss' :team_loss,
                            'gf' : team_gf,
                            'ga' : team_ga,
                            'points' : (team_wins * 3) + team_draws,
                            'played' : team_wins + team_draws + team_loss,
                            'gd' : team_gf - team_ga,
                            'position' : i,
                            'result' : str(template.get("result"+str(i)).value).split()[0].upper() if template.has("result" + str(i)) else "",
                        }
                    table.append(team)
                    i += 1
                #table = sorted(table, key=lambda k: k['position'])
                #tables.append(table)
        return pd.DataFrame(table)

class WikiPageTables(WikiPage):
    def __init__(self, title, section):
        super(WikiPageTables, self).__init__(title)
        self.title = title
        self.section = section
        self.tables = self._parse_tables()

    def _parse_tables(self):
        print(self.wikicode)
        wc = mwparserfromhell.parse(self.wikicode.get_sections(matches=self.section))
        tbl = []
        for t in wc.filter_tags():
            if t.tag == "table":
                tbl.append(mwparserfromhell.parse(t.contents))
        page_tables = []
        for ts in tbl:
            h = []
            c = []
            rows = 0
            for r in ts.filter_tags():
                if r.tag == 'th':
                    h.append(r.contents.strip())
                elif r.tag == 'tr':
                    rows +=1

            c = [["" for i in range(0,len(h))] for j in range(0,rows)]
            i = 0
            for r in ts.filter_tags():
                if r.tag == 'tr':
                    j = 0
                    for s in mwparserfromhell.parse(r.contents).filter_tags():
                        while c[i][j] != "":
                            j+=1
                        c[i][j] = s.contents.strip_code()

                        if s.has("rowspan"):
                            rs = int(s.get("rowspan").split("=")[1])
                            for k in range(0,rs):
                                c[i+k][j] = s.contents.strip_code()
                        pass
                    i +=1

            page_tables.append(c)
        return page_tables
