import mwparserfromhell
import urllib.request
import urllib.parse
import re
import parsedatetime
import datetime
import time as timelib
import json
import string
import os
from PIL import Image
import logging
import pandas as pd
import numpy as np

class WikiPage(object):
    pass;
    #competition_text = {"Serie A" : "Ser A", "Champions League" : "UCL", "Europa League" : "EL", "Coppa Italia": "CI", "Friendly": "Fr"}
    _api_url = "https://en.wikipedia.org/w/api.php"

    def __init__(self, title):
        self.title = title
        self.wikicode = self._get_page()

    def _get_page(self):

        print("Getting Page: " + self.title + ".")
        data = {"action": "query", "prop": "info|revisions", "inprop":"url", "rvlimit": 1,"rvprop": "content", "format": "json", "titles": self.title}
        response = urllib.request.urlopen(self._api_url, urllib.parse.urlencode(data).encode()).read()
        jsonresponse = json.loads(response.decode("utf-8"))
        self.url = list(jsonresponse["query"]["pages"].values())[0]["fullurl"]
        try:
            return mwparserfromhell.parse(list(jsonresponse["query"]["pages"].values())[0]["revisions"][0]['*'])
        except:
            return None

    def _get_text(self,wikicode):
        return wikicode.strip_code().strip()

    def _get_timestamp (self, date, time):
        date = self._get_text(date)
        time = self._get_text(time)
        dt = timelib.mktime(timelib.strptime('24/05/2030', "%d/%m/%Y"))
        if len(date) > 0:
            date = date + ' ' + re.sub(r'\([^)]*\)', '', time)
            d = parsedatetime.Calendar()
            time_struct, parse_status = d.parse(date)
            dt = timelib.mktime(time_struct)
        return dt

    def _merge_date_time (self, date, time):
        dt = datetime.datetime.fromtimestamp(self._get_timestamp(date,time))
        return dt

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
            print("Getting %s." % filename)
            data = {"action": "query", "prop": "imageinfo","iiprop": "url", "format": "json", "iiurlheight": height, "iiurlwidth": width, "titles": image_title}
            response = urllib.request.urlopen(self._api_url, urllib.parse.urlencode(data).encode()).read()
            jsonresponse = json.loads(response.decode("utf-8"))

            image_url = list(jsonresponse["query"]["pages"].values())[0]["imageinfo"][0]["thumburl"]
            temp_image = os.path.join(os.path.dirname(os.path.realpath(__file__)), temp_folder , os.path.basename(image_url))
            urllib.request.urlretrieve(image_url,temp_image)

            tempImage = Image.open(temp_image)
            newImage = Image.new(color_mode, (64,64))
            x, y = tempImage.size
            x1 = int(32 - x/2)
            y1 = int(32 - y/2)
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

        s = str(wikicode.get_sections(flat=True).pop(0))
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

                print ("Using image %s" % im)
                if im[-4] == ".":
                    wiki_image = WikiImage(im, self.name, os.path.join(os.sep,"usr","share","calciodb","potm-images"), "LA")
                    self.image_path = wiki_image.image_path
                else:
                    self.image_path = None
        self.appearances = total_app
        return {"content": title + profile + "##Bio\n\n" + s, "title":"[Player of the Month] " +  self.name + " (" + str(total_app)+" caps)",'name': self.name, 'caps':total_app }

class WikiSeason(WikiPage):
    def __init__(self, title):
        super(WikiSeason,self).__init__(title)
        self.title = title
        self.year = title[2:7].replace('–','-')
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
                r = {
                        'season': self.year,
                        'home_team' : self._get_text(template.get("team1").value),
                        'home_full_name': str(team1_full),
                        'away_team' : self._get_text(template.get("team2").value),
                        'away_full_name':str(team2_full),
                        'referee' : ref_name,
                        'time' : self._get_timestamp(template.get("date").value, template.get("time").value)
                    }

                stadium_name = "N/A"
                try:
                    stadium_name = self._get_text(template.get("stadium").value).strip()
                except:
                    pass
                stadium = stadium_name
                goals = self._get_text(template.get("score").value).split(u'\u2013')

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

                if template.has("round"):
                    comp = template.get("round").value

                    comp_title = self._get_text(comp)
                    r['competition'] =  comp_title if len(comp_title.split()) == 1 else ".".join( [ w[0] for w in comp_title.split() ] )

                    if comp.strip_code().strip().isdigit():
                        r['competition'] = "Ser A"
                    if "Champions League" in comp:
                        r['competition'] = "UCL"
                    if "Europa League" in comp:
                        r['competition'] = "EL"
                    if "Coppa Italia" in comp:
                        r['competition'] = "CI"
                    if "Friendly" in comp:
                        r['competition'] = "Fr"
                print(r)
                if len(r['home_team']) > 1 or len(r['away_team']) > 1:
                    events = pd.concat([events,self._get_events_dict(template.get('goals1').value.split("<br>"),r,r['home_team'])]) if "<br>" in template.get('goals1').value else pd.concat([events,self._get_events_dict(template.get('goals1').value.split("<br/>"),r,r['home_team'])])
                    events = pd.concat([events,self._get_events_dict(template.get('goals2').value.split("<br>"),r,r['away_team'])]) if "<br>" in template.get('goals2').value else pd.concat([events,self._get_events_dict(template.get('goals2').value.split("<br/>"),r,r['away_team'])])
                    matches = pd.concat([matches,pd.DataFrame([r])])

            elif ("Serie A" in template.name) or ("Champions League" in template.name) or ("Europa League" in template.name):
                wt = WikiTable(str(template.name))
                tables = pd.concat( [tables, wt.tables ] )

        print(matches)
        matches.sort_values(by="time", inplace=True)

        return {'club':club, 'matches':matches, 'events':events, 'tables': tables}

    def _get_events_dict(self, team_events, r, team): # team_events as List
        events_list = []
        match_time = r['time']
        for i,event in enumerate(team_events):
            player_name = self._get_text(mwparserfromhell.wikicode.parse_anything(event))
            player_name = ''.join(ch for ch in player_name if ch not in set(string.punctuation)).strip()

            for t in mwparserfromhell.wikicode.parse_anything(event).filter_templates():
                if t.name == "goal" or t.name == "yel":
                    for i in range(0, len(t.params), 2):
                        event_desc = t.params[i+1] if len(t.params) > i+1 else ""
                        event_time = t.params[i].split('+')[0].strip()
                        if event_time.isdigit():
                            events_list.append({'time' : event_time, 'player': player_name, 'type': str(t.name), 'desc' : event_desc, 'match_time':match_time, 'team': team, 'season':r['season']})
                elif t.name == "sent off":
                    event_desc = "strt" if t.params[0] == '0' else "dbly"
                    event_time = t.params[1].strip()
                    if event_time.isdigit():
                        events_list.append({'time' : event_time, 'player': player_name,'type': str(t.name), 'desc' : str(event_desc), 'match_time':match_time, 'team': team, 'season':r['season']})
        return pd.DataFrame(events_list)

class WikiTable(WikiPage):
    def __init__(self, title):
        super(WikiTable, self).__init__('Template:' + title)
        self.title = 'Template:' + title
        self.tables = self._parse_table()

    def _parse_table(self):
        i = 1
        j = True

        table = []
        for template in self.wikicode.filter_templates():
            if "Sports table" in template.name:
                #table = []
                while template.has("team" + str(i)):
                    team_code = str(template.get("team" + str(i)).value).split()[0].strip()
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
