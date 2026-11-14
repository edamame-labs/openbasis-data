"""Sitting governors from each state's official governor website; no fallback inputs.

Each rule names one element of the governor's own homepage that identifies the
officeholder (page title, a heading, or a meta description), with a pattern that
must match at least once and yield exactly one distinct name. A missing or
ambiguous match stops the build. Sites that refuse plain HTTP retrieval are
listed in BLOCKED and recorded as not collected rather than filled from another
publisher.

The governor sites do not state a party. Where a second page or PDF published by
the same state's government does (PARTY_RULES), `party` comes from that document
and carries field evidence; other governors have no party.
"""
import html
import io
import logging
import re
import unicodedata
from build import record

NAMES = dict(AL='Alabama', AK='Alaska', AZ='Arizona', AR='Arkansas', CA='California', CO='Colorado', CT='Connecticut', DE='Delaware',
             FL='Florida', GA='Georgia', HI='Hawaii', ID='Idaho', IL='Illinois', IN='Indiana', IA='Iowa', KS='Kansas', KY='Kentucky',
             LA='Louisiana', ME='Maine', MD='Maryland', MA='Massachusetts', MI='Michigan', MN='Minnesota', MS='Mississippi',
             MO='Missouri', MT='Montana', NE='Nebraska', NV='Nevada', NH='New Hampshire', NJ='New Jersey', NM='New Mexico',
             NY='New York', NC='North Carolina', ND='North Dakota', OH='Ohio', OK='Oklahoma', OR='Oregon', PA='Pennsylvania',
             RI='Rhode Island', SC='South Carolina', SD='South Dakota', TN='Tennessee', TX='Texas', UT='Utah', VT='Vermont',
             VA='Virginia', WA='Washington', WV='West Virginia', WI='Wisconsin', WY='Wyoming')

N = r"(?P<name>[A-Z][A-Za-z.'\- ]+?)"
TITLE = r'<title[^>]*>\s*'
# state: (publisher, url, pattern). Patterns run on the HTML-unescaped page with whitespace collapsed.
# A rule whose URL contains the governor's name (ND) stops the build when the office changes hands.
RULES = {
 'AL': ('Office of the Governor of Alabama', 'https://governor.alabama.gov/', r'<p>Governor '+N+r', who became the \d+\w+ Governor of Alabama'),
 'AK': ('Office of the Governor of Alaska', 'https://gov.alaska.gov/', TITLE+r'Governor \w+ Home - '+N+r'\s*</title>'),
 'AZ': ('Office of the Arizona Governor', 'https://azgovernor.gov/', TITLE+r'Office of the Arizona Governor '+N+r'\s*</title>'),
 'AR': ('Office of the Governor of Arkansas', 'https://governor.arkansas.gov/', TITLE+r'Home Page - Arkansas Governor - '+N+r'\s*</title>'),
 'CA': ('Office of the Governor of California', 'https://www.gov.ca.gov/', r'<meta name="description" content="The official website of California Governor '+N+r'\. '),
 # governor.colorado.gov accepted no connections (Nov 2026); the state portal serves the same office's site.
 'CO': ('Office of the Governor of Colorado', 'https://www.colorado.gov/governor/', TITLE+r"Colorado Governor's Office Home Page \| Colorado Governor "+N+r'\s*</title>'),
 'CT': ('Office of the Governor of Connecticut', 'https://portal.ct.gov/governor', TITLE+r'Connecticut Governor '+N+r' \| CT\.gov\s*</title>'),
 'DE': ('Office of the Governor of Delaware', 'https://governor.delaware.gov/', TITLE+r'Governor '+N+r' - State of Delaware\s*</title>'),
 'FL': ('Executive Office of the Governor of Florida', 'https://www.flgov.com/eog/', TITLE+r'Governor '+N+r' \| Executive Office of the Governor\s*</title>'),
 'GA': ('Office of the Governor of Georgia', 'https://gov.georgia.gov/', TITLE+r'Governor '+N+r' Office of the Governor\s*</title>'),
 'HI': ('Office of the Governor of Hawaii', 'https://governor.hawaii.gov/', TITLE+r'Governor '+N+r', M\.D\. - Office of the Governor\s*</title>'),
 'ID': ('Office of the Governor of Idaho', 'https://gov.idaho.gov/', r'<meta property="og:title" content="Governor '+N+r'">'),
 'IL': ('Office of the Governor of Illinois', 'https://gov.illinois.gov/', TITLE+N+r', Governor\s*</title>'),
 'IN': ('Office of the Governor of Indiana', 'https://www.in.gov/gov/', r'<h1\s*>Indiana Governor '+N+r'</h1>'),
 'IA': ('Office of the Governor of Iowa', 'https://governor.iowa.gov/', r'<meta property="og:site_name" content="Governor '+N+r'" />'),
 # Browser-captured (see BROWSER); the menu link to the governor's page carries the name. Redirects to www.governor.ks.gov.
 'KS': ('Office of the Governor of Kansas', 'https://governor.kansas.gov/', r'<a class="megamenu_level1" href="/about-the-office/governor-[a-z-]+" aria-label="Governor '+N+r'"'),
 'KY': ('Office of the Governor of Kentucky', 'https://governor.ky.gov/', TITLE+r'Welcome - Kentucky Governor '+N+r'\s*</title>'),
 'LA': ('Office of the Governor of Louisiana', 'https://gov.louisiana.gov/', TITLE+r'Home \| Office of Governor '+N+r'\s*</title>'),
 'ME': ('Office of the Governor of Maine', 'https://www.maine.gov/governor/mills/', TITLE+r'Home \| Office of Governor '+N+r'\s*</title>'),
 'MA': ('Office of the Governor of Massachusetts', 'https://www.mass.gov/orgs/office-of-the-governor', TITLE+r'Governor '+N+r' and Lt\. Governor [^|<]+ \| Mass\.gov\s*</title>'),
 'MD': ('Office of the Governor of Maryland', 'https://governor.maryland.gov/', TITLE+r'The Office of Governor '+N+r'\s*</title>'),
 'MI': ('Office of the Governor of Michigan', 'https://www.michigan.gov/whitmer', TITLE+r'Governor '+N+r'\s*</title>'),
 'MN': ('Office of the Governor of Minnesota', 'https://mn.gov/governor/', r'<meta property="og:site_name" content="Office of Governor '+N+r' and Lt\. Governor [^"]+">'),
 'MS': ('Office of the Governor of Mississippi', 'https://governorreeves.ms.gov/', TITLE+r'Official Website of Mississippi Governor '+N+r'\s*</title>'),
 'MO': ('Office of the Governor of Missouri', 'https://governor.mo.gov/', TITLE+N+r', Governor of Missouri Homepage'),
 'MT': ('Office of the Governor of Montana', 'https://governor.mt.gov/', TITLE+r'Montana Governor '+N+r' Official Website\s*</title>'),
 'NE': ('Office of the Governor of Nebraska', 'https://governor.nebraska.gov/', TITLE+r'Latest News \| Office of Governor '+N+r'\s*</title>'),
 'NV': ('Office of the Governor of Nevada', 'https://www.gov.nv.gov/', TITLE+r"Nevada Governor's Office \| "+N+r'\s*</title>'),
 'NH': ('Office of the Governor of New Hampshire', 'https://www.governor.nh.gov/', r'<meta property="og:site_name" content="Governor '+N+r'">'),
 'NJ': ('Office of the Governor of New Jersey', 'https://www.nj.gov/governor/', TITLE+r'Office of New Jersey Governor '+N+r'\s*</title>'),
 'NM': ('Office of the Governor of New Mexico', 'https://www.governor.state.nm.us/', TITLE+r'Home - Office of the Governor - '+N+r'\s*</title>'),
 'NY': ('Office of the Governor of New York', 'https://www.governor.ny.gov/', r'<meta property="og:site_name" content="Governor '+N+r'"\s*/?>'),
 'NC': ('Office of the Governor of North Carolina', 'https://governor.nc.gov/', r'<meta name="description" content="The official website for North Carolina Governor '+N+r'\." />'),
 # The homepage names the governor only in news items; its "Governor" menu links to this biography page.
 'ND': ('Office of the Governor of North Dakota', 'https://www.governor.nd.gov/governor-kelly-armstrong', TITLE+r'Governor '+N+r' \| North Dakota Office of the Governor\s*</title>'),
 'OH': ('Office of the Governor of Ohio', 'https://governor.ohio.gov/', TITLE+r'Governor '+N+r'\s*</title>'),
 'OK': ('Office of the Governor of Oklahoma', 'https://oklahoma.gov/governor.html', TITLE+r'Governor '+N+r'\s*</title>'),
 'OR': ('Office of the Governor of Oregon', 'https://www.oregon.gov/gov/Pages/index.aspx', TITLE+r'Governor of Oregon : Governor '+N+r' : State of Oregon\s*</title>'),
 'PA': ('Office of the Governor of Pennsylvania', 'https://www.pa.gov/governor', r'<meta name="copapwp-page-title" content="Governor '+N+r'"/>'),
 'RI': ('Office of the Governor of Rhode Island', 'https://governor.ri.gov/', TITLE+r'Welcome to the Office of Governor '+N+r" \| Governor's Office, State of Rhode Island\s*</title>"),
 'SC': ('Office of the Governor of South Carolina', 'https://governor.sc.gov/', TITLE+r'Home \| S\.C\. Governor '+N+r'\s*</title>'),
 'SD': ('Office of the Governor of South Dakota', 'https://governor.sd.gov/governor/about.aspx', TITLE+r'South Dakota Governor '+N+r'\s*</title>'),
 # The title is only "Governor"; the footer link to the governor's biography carries the name.
 'TN': ('Office of the Governor of Tennessee', 'https://www.tn.gov/governor.html', r'<a href="/governor/about-[a-z-]+\.html" aria-label="Governor '+N+r'" title="Governor [^"]+">'),
 'TX': ('Office of the Texas Governor', 'https://gov.texas.gov/', TITLE+r'Office of the Texas Governor \| '+N+r'\s*</title>'),
 'UT': ('Office of the Governor of Utah', 'https://governor.utah.gov/', TITLE+r'Governor '+N+r'\s*</title>'),
 'VT': ('Office of the Governor of Vermont', 'https://governor.vermont.gov/', TITLE+r'Home \| Office of Governor '+N+r'\s*</title>'),
 'VA': ('Office of the Governor of Virginia', 'https://www.governor.virginia.gov/', r'<meta name="description" content="'+N+r', Commonwealth, Governor of Virginia'),
 'WA': ('Office of the Governor of Washington', 'https://governor.wa.gov/', TITLE+r'Home \| Governor '+N+r'\s*</title>'),
 'WV': ('Office of the Governor of West Virginia', 'https://governor.wv.gov/', TITLE+r'WV Office of the Governor '+N+r'\s*</title>'),
 'WI': ('Office of the Governor of Wisconsin', 'https://evers.wi.gov/Pages/Home.aspx', TITLE+r'Official site of Governor '+N+r'\s*</title>'),
 'WY': ('Office of the Governor of Wyoming', 'https://governor.wyo.gov/', TITLE+r'Wyoming Governor '+N+r'\s*</title>'),
}
# Sources read from an imported browser DOM observation (tools/import_snapshot.py), not over HTTP.
BROWSER = {'gov-ks', 'gov-mi', 'gov-mn', 'gov-nh', 'gov-ri'}
# Official governor sites with no collected observation: they refused retrieval with USER_AGENT
# (bot challenge, 403 or timeout) and have no imported browser capture. No other publisher substitutes for them.
BLOCKED = {}
assert set(RULES) | set(BLOCKED) == set(NAMES) and not set(RULES) & set(BLOCKED)
assert all(k.removeprefix('gov-').upper() in RULES for k in BROWSER)


# Party. state: (publisher, url, pattern, effective period or None). Each page or PDF is published by a government body
# of the same state (in Ohio, a county board of elections) and states a party beside a person's name: an officials roster, a list of the state's governors, or the
# official results or candidate list of the election that began the governor's term. The pattern's name and
# party groups list the people the document names; it runs on the HTML-unescaped page with whitespace collapsed (JSON bodies
# as served, PDFs as the text pdf_text extracts). The governor's party is that of the entries naming the governor
# (same_person), which must agree.
W = r"(?:[A-Z]\.|[A-Z][a-z][A-Za-z'\-]*)"  # a capitalised word or an initial, for names in PDF text
PARTY_RULES = {
 'AK': ('Alaska Division of Elections', 'https://www.elections.alaska.gov/candidates/?election=22genr',
        r'</a><strong>(?P<name>[^<(/]+?) \(Registered (?P<party>[^)]+)\)(?: / [^<]*)?</strong>', '2022-11-08 general election candidate list'),
 'AL': ('Alabama Department of Archives and History', 'https://archives.alabama.gov/research/guidance/fast-facts/officials/governor.aspx',
        r'<tr> <td>[^<]*</td> <td>(?:<a [^>]*>)?(?P<name>[^<]+?)(?:</a>)?</td> <td>[^<]*</td> <td>[^<]*</td> <td>(?P<party>[^<]+?)</td>', None),
 'AR': ('Arkansas House of Representatives', 'https://www.arkleg.state.ar.us/Home/FTPDocument?path=%2Fassembly%2F2023%2F2023R%2FDocuments%2F2023R+House+Journal.pdf',
        r'(?P<name>[A-Z][a-z]+(?:[ -](?:[A-Z][a-z]+,?|[A-Z][a-z]{0,2}\.))+) \( ?(?P<party>[A-Z]{3})\) [\d,]+ \( ?\d+\.\d+%\)', '2022-11-08 general election'),
 'AZ': ('Arizona Citizens Clean Elections Commission', 'https://www.azcleanelections.gov/Custom/ElectionDataSearch?type=G&sw=A&part=A&inc=A&win=A&cycles=18&offices=2&page=1',
        r'"Party":"(?P<party>[^"]+)","PartyAbbrev":"[^"]*","Initial":[\d.]+,"Matching":[\d.]+,"Independent":[\d.]+,"FullName":"(?P<name>[^"]+)"', '2022-11-08 general election candidate record'),
 'CA': ('California State Library', 'https://governors.library.ca.gov/40-Newsom.html',
        r'<h1>(?P<name>[^<]+)</h1> <h3>[^<]*</h3> <h4>Significant Facts</h4> <p>(?:(?!</p>).)*?<span class="gold">Political Party:</span> (?P<party>[^<]+?) </p>', None),
 'CO': ('Colorado Secretary of State', 'https://www.sos.state.co.us/pubs/elections/Results/Abstract/2022/general/governor.html',
        r'<th scope="col">(?P<name>[^/<(]+?) / [^<(]+? \((?P<party>[A-Z]{3})\)(?: \(Write-in\))?</th>', '2022-11-08 general election'),
 'CT': ('Connecticut Secretary of the State', 'https://portal.ct.gov/sots/register-manual/section-iv/dept-of-social-services--dept-of-veterans-affairs-and-unaffiliated',
        r'<tr> <td[^>]*> <p[^>]*><span[^>]*>(?P<name>[^<]+)</span>(?:<sup><span[^>]*>[^<]*</span></sup>)?</p> </td> <td[^>]*> <p[^>]*><span[^>]*>[^<,]+, (?P<party>[A-Z][A-Za-z.\-]*)</span></p> </td> <td[^>]*> <p[^>]*><span[^>]*>(?:19|20)\d\d-', None),
 'DE': ('Delaware Department of Elections', 'https://elections.delaware.gov/reports/GE2024.html',
        r'<tr><td data-label="Candidate">(?P<name>[^<]+)</td><td data-label="Party">(?P<party>[^<]+)</td>', '2024-11-05 general election'),
 'FL': ('Florida Division of Elections', 'https://dos.elections.myflorida.com/candidates/CanDetail.asp?account=79799',
        r'<font size=\+1 ><b>(?:\d{4} [^<]+)</b></font><b> <br /> [^<]+ </b> <br /> <br /> <font size=\+1 color="#CCOOOO"><b>(?P<name>[^<]+)</b></font> <br /> <b> (?P<party>[^<]+?) </b>', '2022-11-08 general election candidate record'),
 'GA': ('Georgia Secretary of State', 'https://results.sos.ga.gov/cdn/results/Georgia/export-2022NovGen.json',
        r'"name":"(?P<name>[^"()]+?)(?: \(I\))? \([A-Za-z]+\)","ballotOrder":\d+,"voteCount":\d+,"politicalParty":"(?P<party>[A-Za-z]+)"', '2022-11-08 general election'),
 'HI': ('Hawaii Office of Elections', 'https://elections.hawaii.gov/governor-and-lieutenant-governor/',
        r'<td class="column-1">[^<]*</td><td class="column-2">\((?P<party>[A-Z]+)\) (?P<name>[^<*]+)\*?</td>', None),
 'IA': ('Iowa Legislative Services Agency', 'https://www.legis.iowa.gov/docs/publications/RDBKI/1597053.pdf',
        r"(?P<name>[A-Z][A-Za-z.' ]+?) \((?P<party>[A-Z])\) \d{4} –", None),
 'ID': ('Idaho Secretary of State', 'https://voteidaho.gov/idaho-elected-officials/',
        r'<h3 class="elementor-heading-title[^"]*">(?P<name>[^<(]+?) \((?P<party>[A-Z])\)</h3>', None),
 'IL': ('Illinois State Board of Elections', 'https://www.elections.il.gov/ElectionOperations/ElectionVoteTotals.aspx?ID=62',
        r'<a href="CandidateDetailEO\.aspx\?[^"]*"[^>]*>(?P<name>[^<]+)</a><br/></td><td[^>]*>(?P<party>[A-Z][A-Za-z -]*[A-Za-z])</td>', '2022-11-08 general election'),
 'IN': ('Indiana Election Division', 'https://indianavoters.in.gov/ENRHistorical/ExportElectionsToCSV?year=2024&electionType=General&candidateName=&county=&office=Governor%20%26%20Lt.%20Governor&party=&sortBy=&sortDir=&filterCandidateName=&filterElectionType=false',
        r',Governor & Lt\. Governor,(?P<name>[^,]+),(?P<party>[^,]+),Indiana,\d+', '2024-11-05 general election'),
 'KS': ('Kansas Historical Society', 'https://www.kansashistory.gov/kansapedia/laura-kelly/20157',
        r'<h1>(?P<name>[^<]+)</h1> <p[^>]*> (?:<strong>)?(?:<img[^>]*>)?Politician\. (?P<party>[A-Z][a-z]+)\. Born:', None),
 'KY': ('Kentucky State Board of Elections', 'https://elect.ky.gov/results/2020-2029/Documents/Certification%20of%20Election%20Results%20for%202023%20General%20Election%20Final.pdf',
        r'(?P<party>[A-Z][a-z]+) Party (?:[A-Z][a-z]+ Party )*(?:Write-In )?(?P<name>[A-Z][A-Za-z.\'"“” ]*? [A-Z]{2,})(?= )', '2023-11-07 general election'),
 'LA': ('Louisiana Secretary of State', 'https://voterportal.sos.la.gov/ElectionResults/ElectionResults/Data?blob=20231014/RacesCandidates_Multiparish.htm',
        r'"Desc":"(?P<name>(?:[^"\\(]|\\.)+?) \((?P<party>[A-Z]+)\)"(?=(?:(?!"SpecificTitle").)*"SpecificTitle":"Lieutenant Governor")', '2023-10-14 gubernatorial primary election'),
 'MA': ('Secretary of the Commonwealth of Massachusetts', 'https://electionstats.state.ma.us/elections/view/154338/',
        r'<span class="display_name ?"><a href="/candidates/view/[^"]+">(?P<name>[^<]+)</a></span> <br/> <span class="party">(?P<party>[^<]+)</span>', '2022-11-08 general election'),
 'MD': ('Maryland State Board of Elections', 'https://elections.maryland.gov/elections/archive/2022/general_results/gen_results_2022_1.html',
        r'<td class="NameCol"[^>]*> <div> (?P<name>[^<]+?) and [^<]+? (?:<img[^>]*> )?</div> </td> <td class="PartyCol"[^>]*> (?P<party>[^<]+?) </td>', '2022-11-08 general election'),
 'ME': ('Maine State Law and Legislative Reference Library', 'https://legislature.maine.gov/lawlibrary/governors-of-maine-1820/9197',
        r'<tr> <td class="smalllinksblack"[^>]*>(?P<name>[^<]+?)</td> <td class="smalllinksblack"[^>]*>[^<]*\b20\d\d\b[^<]*</td> <td class="smalllinksblack"[^>]*>(?P<party>[^<]+?)</td> </tr>', None),
 'MI': ('Michigan Legislative Service Bureau', 'https://legislature.mi.gov/documents/2025-2026/michiganmanual/Chapter%204.pdf',
        r"(?P<party>[A-Z]) — (?P<name>[A-Z][A-Za-z.' ]+?) ?\.{3,}", None),
 'MN': ('Minnesota Legislative Reference Library', 'https://www.lrl.mn.gov/mngov/gov',
        r'<th[^>]*scope="row"[^>]*>(?P<name>[^<]+)</th><td[^>]*> <span id="[^"]*assumedoffice">[^<]*</span> </td><td> <span id="[^"]*govnum">[^<]*</span> </td><td>(?P<party>[^<]+)</td>', None),
 'MO': ('Missouri State Archives', 'https://www.sos.mo.gov/archives/history/historicallistings/governors',
        r'<td> <p>(?:<span[^>]*>)?\d+\.(?: |<span[^>]*>)*(?:<a [^>]*>)?(?P<name>[^<]+?)(?:</a>)? ?(?:</span>)? ?\((?P<party>[A-Za-z-]+)\)(?=<)', None),
 'MS': ('Mississippi Secretary of State', 'https://www.sos.ms.gov/elections/electionresults/2023General/State%20Certified%20Results/2023%20Statewide%20Recapitulation%20Sheet.pdf',
        r"(?P<name>[A-Z][A-Za-z.'\"\- ]+?) (?P<party>[A-Z][a-z]+) \d+ \d+", '2023-11-07 general election'),
 'MT': ('Montana Historical Society', 'https://mhs.mt.gov/Research/Compass/Facts',
        r'<td[^>]*>[^<]*\d{4}[^<]*</td> <td[^>]*>(?P<name>[^<]+)</td> <td[^>]*>(?: <p>)?(?P<party>[A-Za-z][A-Za-z -]*?)(?:</p> )?</td> </tr>', None),
 'NC': ('North Carolina State Board of Elections', 'https://er.ncsbe.gov/enr/20241105/data/results_0.txt',
        r'"cnm":"NC GOVERNOR[^"]*"[^{}]*?"bnm":"(?P<name>[^"]+)"[^{}]*?"pty":"(?P<party>[^"]+)"', '2024-11-05 general election'),
 'ND': ('State Historical Society of North Dakota', 'https://www.history.nd.gov/exhibits/governors/index.html',
        r'<a href="/exhibits/governors/governors\d+\.html">(?P<name>[^<]+)</a> \((?P<party>[^)]+)\) \d{4}-(?:\d{4}|present)', None),
 'NE': ('Nebraska Legislature', 'https://nebraskalegislature.gov/pdf/bluebook/407-431.pdf',
        r"(?P<name>[A-Z][A-Za-z.' ]+?) \((?P<party>[A-Z])\) ?\.{3,} ?\d{4}", None),
 'NH': ('New Hampshire House of Representatives', 'https://gc.nh.gov/house/calendars_journals/journals/2025/HJ%2002%20January%208,%202025.pdf',
        rf'(?P<name>{W}(?: {W})+), (?P<party>[a-z])(?= )', '2024-11-05 general election'),
 'NJ': ('New Jersey Division of Elections', 'https://www.nj.gov/state/elections/assets/pdf/election-results/2025/2025-official-general-results-governor.pdf',
        r"Name Address (?P<name>[A-Z][A-Z.'\- ]+?)(?: \(w\))? (?=P\.O\.|\d).{5,80}? NJ \d{5} (?P<party>[A-Z][A-Za-z ]+?) ATLANTIC", '2025-11-04 general election'),
 'NM': ('New Mexico Secretary of State', 'https://electionresults.sos.nm.gov/resultsSW.aspx?type=SW&map=CTY&eid=2838',
        r'<div class="col display-results-box-d"> <h1>(?P<name>[^<]+?)(?: AND [^<]+)?</h1> <h2 class="[^"]*">(?P<party>[^<]+)</h2>', '2022-11-08 general election'),
 'NV': ('Nevada State Library, Archives and Public Records', 'https://nsla.nv.gov/archives-governor',
        r'<tr> <td[^>]*>(?P<name>[^<]+)</td> <td[^>]*>(?: <p>)?[^<]*\d{4}[^<]*(?:</p> )?</td> <td[^>]*>(?P<party>[^<]+)</td> </tr>', None),
 'OH': ('Logan County Board of Elections', 'https://www.boe.ohio.gov/logan/c/elecres/20221108results.pdf',
        r"\b(?P<party>[A-Z]{3}) (?P<name>[A-Z][A-Za-z.'\-]+(?: [A-Z][A-Za-z.'\-]+)+?)(?= and [A-Z]| [\d,]+ )", '2022-11-08 general election'),
 'OK': ('Oklahoma Historical Society', 'https://www.okhistory.org/research/governors',
        r'<tr> <td>(?:<strong>)?(?:<a [^>]*>)?(?P<name>[^<]+)(?:</a>)?(?:</strong>)?</td> <td>(?P<party>[A-Za-z][A-Za-z -]*)</td> <td>[^<]*\d{4}[^<]*</td>', None),
 'OR': ('Oregon Secretary of State', 'https://sos.oregon.gov/blue-book/government/Pages/governor-bio.aspx',
        r'<p> ?(?P<name>[A-Z][^,;<>]+), [^;<>]+; (?P<party>[A-Za-z]+); (?:elected|appointed) \d{4}; term expires', None),
 'PA': ('Pennsylvania Department of State', 'https://www.electionreturns.pa.gov/api/ElectionReturn/GET?methodName=GetSummaryData&electionid=94&electiontype=G&isactive=0',
        r'\\"OfficeName\\":\\"Governor\\",\\"CandidateName\\":\\"(?P<name>[^"\\]+?) *\\",\\"PartyName\\":\\"(?P<party>[^"\\]+)\\"', '2022-11-08 general election'),
 'RI': ('Rhode Island Board of Elections', 'https://www.ri.gov/election/results/2022/general_election/races/3.html',
        r'<td scope="row" class="candidate" data-title="Candidate">(?P<party>[A-Za-z]+) (?P<name>[^<]+?) <span class="smalltext">\((?P=party)\)</span>', '2022-11-08 general election'),
 'SC': ('South Carolina Legislature', 'https://www.scstatehouse.gov/man26/04_Gov.pdf',
        r"(?P<name>[A-Z][A-Za-z'\-]+, [A-Z][A-Za-z. ]+?) \[(?P<party>[A-Z])\]—\(", None),
 'SD': ('South Dakota Secretary of State', 'https://sdsos.gov/elections-voting/election-resources/current-elected-officials.aspx',
        r'<strong>(?P<office>U\.S\. Senator|U\.S\. Representative|Governor|Lt\. Governor|Secretary of State|Attorney General|State Auditor|State Treasurer) (?P<name>[^<(]+?) \((?P<party>[A-Z])\)\s*</strong>', None),
 'TN': ('Tennessee Secretary of State', 'https://publications.tnsosfiles.com/pub/blue_book/25-26/25-26_Executive.pdf',
        rf'(?P<name>{W}(?: {W})+) \((?P<party>[A-Z])\) Governor of Tennessee', None),
 'TX': ('Legislative Reference Library of Texas', 'https://lrl.texas.gov/legeLeaders/governors/govBrowse.cfm',
        r'<th scope="row"><a href="govPage\.cfm\?governorID=\d+">\s*(?P<name>[^<]+?)\s*</a>\s*</th>\s*<td align="center">\s*(?P<party>[^<]*?)\s*<br>', None),
 'UT': ('Utah Historical Society', 'https://historytogo.utah.gov/post/governors/',
        r'<strong>(?:<img[^>]*>)?\s*(?:<a [^>]*>)?\s*(?P<name>[^<]+?)\s*(?:</a>)?</strong></p> <p>[A-Z][a-z-]+ Governor of the State of Utah from [^<]*<br ?/?>\s*(?P<party>[^<]+?)\s*</p>', None),
 'VA': ('Virginia Department of Elections', 'https://historical.elections.virginia.gov/contest/164996',
        r'"party":\{"id":"\d+","name":"(?P<party>[^"]+)"[^{}]*\},"party2":(?:null|\{[^{}]*\}),"party3":(?:null|\{[^{}]*\}),"party4":(?:null|\{[^{}]*\}),"__typename":"CandidateInContest","voteChannelId":\d+,"candidate":\{[^{}]*\},"shortDisplayName":"(?:[^"\\]|\\.)*","displayName":"(?P<name>(?:[^"\\]|\\.)+)"', '2025-11-04 general election'),
 'VT': ('Vermont Secretary of State', 'https://electionarchive.vermont.gov/contest/160972',
        r'"party":\{"id":"\d+","name":"(?P<party>[^"]+)"[^{}]*\},"party2":(?:null|\{[^{}]*\}),"party3":(?:null|\{[^{}]*\}),"party4":(?:null|\{[^{}]*\}),"__typename":"CandidateInContest","voteChannelId":\d+,"candidate":\{[^{}]*\},"shortDisplayName":"(?:[^"\\]|\\.)*","displayName":"(?P<name>(?:[^"\\]|\\.)+)"', '2024-11-05 general election'),
 'WA': ('Washington State Library', 'https://www.sos.wa.gov/library/research-collections/washington-territorial-and-state-governors',
        r'<tr> <td>(?P<name>[^<]+?)\s*</td> <td>\s*(?P<party>[A-Za-z][^<]*?)\s*</td> <td>\s*\d', None),
 'WI': ('Wisconsin Legislative Reference Bureau', 'https://docs.legis.wisconsin.gov/misc/lrb/blue_book/2025_2026/020_elected_officials.pdf',
        rf'(?P<name>{W}(?: {W})+), (?:Governor|Lieutenant Governor|Attorney General|Secretary of State|State Treasurer) (?P<party>[A-Z][a-z]+) Personal:', None),
 'WV': ('West Virginia Secretary of State', 'https://apps.sos.wv.gov/elections/candidate-search/candidate.aspx?candidate=22761',
        r'<tr><td><strong>(?P<name>[^<]+?)\s*(?:</?strong>)+<br ?/?></td><td>(?P<party>[^<]+?)</td>', '2024 election candidate record'),
 'WY': ('Wyoming Secretary of State', 'https://sos.wyo.gov/Services/docs/GovernorRoster.pdf',
        rf'(?:(?<=\d{{4}} )|(?<=Office ))(?P<name>{W}(?: {W})+) \((?P<party>[A-Z])\) [A-Z][a-z]{{2}}\. \d', None),
}
# Governors with no party: no page or PDF of the state's government that states it could be read over plain HTTP with USER_AGENT.
# Nothing else substitutes for one (no association, encyclopedia, news or party source).
# PDFs read only in part: the pages (a slice, from 0) that hold the entries. The Arkansas journal has 3,547 pages and
# prints the declared results of the 2022 general election in the second day's proceedings.
PDF_PAGES = {'AR': slice(0, 200)}
PARTY_NOT_COLLECTED = {
 'NY': "State Board of Elections hosts returned a Cloudflare challenge (HTTP 403); the State Library's list of governors, the Governor's site and the open-data campaign filer records name no party.",
}
assert set(PARTY_RULES) | set(PARTY_NOT_COLLECTED) == set(NAMES) and not set(PARTY_RULES) & set(PARTY_NOT_COLLECTED)
# Labels the party pages use, as published. An unlisted label stops the build.
PARTY_LABELS = {'r': 'Republican', 'rep': 'Republican', 'republican': 'Republican',
                'd': 'Democratic', 'dem': 'Democratic', 'democrat': 'Democratic', 'democratic': 'Democratic',
                'democratic-farmer-labor': 'Democratic-Farmer-Labor'}

SOURCES = {'gov-'+st.lower(): (publisher, url) for st, (publisher, url, _) in RULES.items()}
PARTY_SOURCES = {'gov-party-'+st.lower(): (publisher, url) for st, (publisher, url, _, _) in PARTY_RULES.items()}
EXECUTIVE = {st: dict(governor='collected' if st in RULES else 'not-collected',
                      blockers=[] if st in RULES else ['The official governor website refused automated retrieval: '+BLOCKED[st]])
             for st in NAMES}
BODY = '{} Executive'
# Several state sites reject curl's default agent; this one identifies the project and is recorded in provenance.
USER_AGENT = 'Mozilla/5.0 (compatible; OpenBasisData/1.0; +https://github.com/edamame-labs/openbasis-data)'


def governor_name(state, raw):
    """The single governor name the state's rule extracts from its homepage."""
    page = ' '.join(html.unescape(raw.decode('utf-8', 'replace')).split())
    names = {' '.join(m.group('name').split()) for m in re.finditer(RULES[state][2], page)}
    assert len(names) == 1, (state, 'Expected exactly one governor name', sorted(names))
    name = names.pop()
    assert 2 <= len(name.split()) <= 5 and not re.search(r'\b(?:Office|Governor|Home|Welcome|State)\b', name), (state, name)
    return name


def parse(key, raw, source):
    state = key.removeprefix('gov-').upper()
    row = record(source, f'{state.lower()}-governor', governor_name(state, raw), state, 'state', BODY.format(NAMES[state]))
    row.update(office='Governor', website=source['url'])
    return [row]


SUFFIXES = {'jr', 'sr', 'ii', 'iii', 'iv'}


def folded(text):
    """Letters only, without accents or case."""
    text = unicodedata.normalize('NFKD', text)
    return re.sub(r'[^a-z]', '', ''.join(c for c in text if not unicodedata.combining(c)).casefold())


def name_parts(name):
    """(given names, family name), folded, from 'Given ... Family' or 'Family, Given ...'.

    Generational suffixes are dropped; a quoted or bracketed nickname counts as a given name; the family name is the last word.
    """
    pieces = [[t for t in piece.split() if folded(t) and folded(t) not in SUFFIXES] for piece in name.split(',')]
    pieces = [p for p in pieces if p]
    tokens = [folded(t) for t in (pieces[1] + pieces[0] if len(pieces) == 2 else [t for p in pieces for t in p])]
    return tokens[:-1], tokens[-1] if tokens else ''


def given_names_agree(a, b):
    """Equal, or one a prefix of the other of at least three letters (Dan / Daniel, Josh / Joshua)."""
    short, long = sorted((a, b), key=len)
    return a == b or (len(short) >= 3 and long.startswith(short))


def same_person(governor, listed):
    """The party page's entry names the governor: same family name, and one name's first given name is among the other's given names."""
    given_a, family_a = name_parts(governor)
    given_b, family_b = name_parts(listed)
    if not given_a or not given_b or family_a != family_b: return False
    return any(given_names_agree(given_a[0], t) for t in given_b) or any(given_names_agree(given_b[0], t) for t in given_a)


def pdf_text(raw, pages=slice(None)):
    """The text of a PDF's pages, page by page in reading order. Needs pypdf (requirements-geo.txt)."""
    import pypdf
    logging.getLogger('pypdf').setLevel(logging.ERROR)
    return '\n'.join(page.extract_text() for page in pypdf.PdfReader(io.BytesIO(raw)).pages[pages])


def governor_party(state, raw, governor):
    """The one party the state's party page states for the entries that name the governor."""
    page = ' '.join((pdf_text(raw, PDF_PAGES.get(state, slice(None))) if raw[:5] == b'%PDF-' else html.unescape(raw.decode('utf-8', 'replace'))).split())
    listed = [(' '.join(m.group('name').split()), ' '.join(m.group('party').split())) for m in re.finditer(PARTY_RULES[state][2], page)]
    assert listed, (state, 'Party page lists nobody; the page changed')
    labels = {party for name, party in listed if same_person(governor, name)}
    assert len(labels) == 1, (state, 'Expected exactly one party for the governor on the party page', governor, sorted(labels))
    label = labels.pop()
    key = re.sub(r' party$', '', label.casefold())
    assert key in PARTY_LABELS, (state, 'Unmapped party label', label)
    return PARTY_LABELS[key]


def add_party(row, party, source):
    row['party'] = party
    row['sources'] = row['sources'] + [source]
    row['fieldEvidence'] = dict(party=dict(value=party, sourceIds=[source['id']]))
    return row


def collect(acquire, offline):
    rows, sources = [], []
    for key, (publisher, url) in SOURCES.items():
        raw, source = acquire(key, publisher, url, offline, **({} if key in BROWSER else dict(user_agent=USER_AGENT)))
        row, = parse(key, raw, source)
        sources.append(source)
        if row['state'] in PARTY_RULES:
            party_key = 'gov-party-' + row['state'].lower()
            raw, evidence = acquire(party_key, *PARTY_SOURCES[party_key], offline, user_agent=USER_AGENT)
            if PARTY_RULES[row['state']][3]: evidence['effectivePeriod'] = PARTY_RULES[row['state']][3]
            add_party(row, governor_party(row['state'], raw, row['name']), evidence)
            sources.append(evidence)
        rows.append(row)
    return rows, sources
