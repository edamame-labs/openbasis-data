"""Regression checks for current/terminated and multi-member roster semantics."""
import json
import unittest
from unittest.mock import patch
from regions import region_c as r


class RegionC(unittest.TestCase):
    def source(self, key):
        return {'url':r.SOURCES[key][1], 'id':key}

    def test_vermont_excludes_resigned_and_preserves_multi_member_district(self):
        people=[dict(PersonTypeID='S',PersonID=str(i),FirstName='Given'+str(i),
                     LastName='Family',NameSuffix='',District='Chittenden-Central District',
                     Party='Democrat',TerminationReason='')for i in range(30)]
        people.append(dict(people[0],PersonID='former',TerminationReason='Resigned October 27, 2025'))
        rows=r.parse('vt-upper',json.dumps({'data':people}).encode(),self.source('vt-upper'))
        self.assertEqual(len(rows),30)
        self.assertEqual(len({row['id']for row in rows}),30)
        self.assertEqual(len({row['district']for row in rows}),1)
        self.assertFalse(any('former' in row.get('website','')for row in rows))

    def test_name_suffix_remains_after_family_name(self):
        self.assertEqual(r.given_first('Fowler, Hyland Buddy, Jr.'),'Hyland Buddy Fowler, Jr.')

    def test_wrong_south_dakota_current_session_stops_import(self):
        raw=json.dumps([{'CurrentSession':True,'SpecialSession':False,'SessionId':174,'Year':'2027'}]).encode()
        with self.assertRaisesRegex(AssertionError,'session changed'):
            r.parse('sd-session',raw,self.source('sd-session'))

    def test_texas_inactive_placeholder_is_not_an_official(self):
        members=[dict(member_name='Person, Current',id=1,member_bill_code=100,
                      active=1,link='https://house.texas.gov/members/100'),
                 dict(member_name='District 2',id=2,member_bill_code=200,
                      active=0,link='https://house.texas.gov/members/200')]
        import html
        raw=('<get-members :members="'+html.escape(json.dumps(members),quote=True)+'"></get-members>').encode()
        with patch.dict(r.LIMITS,{'TX':(31,1)}):
            rows=r.parse('tx-lower',raw,self.source('tx-lower'))
        self.assertEqual([row['name']for row in rows],['Current Person'])

    def test_tennessee_requires_115th_assembly_and_skips_district_less_lt_governor(self):
        with self.assertRaisesRegex(AssertionError,'session changed'):
            r.parse('tn-upper',b'<a href="?ga=114">Previous assembly</a>',self.source('tn-upper'))
        with self.assertRaisesRegex(AssertionError,'session changed'):
            r.parse('tn-upper',b'<a href="?ga=115"></a><a href="?ga=116">Future assembly</a>',self.source('tn-upper'))
        def tr(name,label):
            return '<tr><td><a href="/apps/LegislatorInfo/Member?ga=115&amp;id=1">'+name+'</a></td><td>'+label+'</td><td>R</td><td>x</td><td>x</td><td>x</td><td>(615) 741-0000</td></tr>'
        raw=('<a href="?ga=115"></a><table>'+tr('Person, Ann','District 4')+tr('Officer, Lee','Lt. Governor')+'</table>').encode()
        source=self.source('tn-upper')
        with patch.dict(r.LIMITS,{'TN':(1,1)}):
            rows=r.parse('tn-upper',raw,source)
        self.assertEqual([(x['name'],x['district']) for x in rows],[('Ann Person','4')])
        self.assertEqual(len(source['excludedEntries']),1)

    def test_missing_structure_never_publishes_empty_roster(self):
        with self.assertRaises(AssertionError):
            r.parse('wa-roster',b'<p>2025-26 biennium: temporarily unavailable</p>',self.source('wa-roster'))

    def test_person_id_is_independent_of_district_and_non_government_links_omitted(self):
        source=self.source('vt-upper')
        a=r.make(source,'VT','upper','A','Same named district','1',website='https://campaign.example/')
        b=r.make(source,'VT','upper','B','Same named district','2')
        self.assertNotEqual(a['id'],b['id'])
        self.assertNotIn('website',a)

    @staticmethod
    def ri_page(chamber, identity, active='Yes', next_page=False):
        headers=['LinkTitle','first_name','middle_name','last_name','suffix','legislator_name',
                 'chamber','city','political_party','district','email','leadership_role','phone',
                 'legislator_bioURL','file_Name','ActiveFlag','ID']
        values=['title','Given','','Family','','Given Family',chamber,'','Democrat','1','','','',
                'https://www.rilegislature.gov/senators/person/Pages/Biography.aspx','',active,identity]
        text=''.join('<div name="'+key+'" DisplayName="'+key+'"></div>'for key in headers)
        text+='<table><tr iid="1,'+identity+'"><td></td>'+''.join('<td>'+v+'</td>'for v in values)+'</tr></table>'
        if next_page:
            text+='''<a onclick='RefreshPageTo(event, "/Lists/legislationInformation/AllItems.aspx?Paged=TRUE&amp;p_ID=30&amp;PageFirstRow=31");' href="javascript:"></a>'''
        return text.encode()

    def test_unknown_active_status_requires_review(self):
        with self.assertRaisesRegex(AssertionError,'active flag'):
            r.parse('ri-roster',self.ri_page('Senate','1','Unresolved'),self.source('ri-roster'))

    def test_conflicting_single_member_district_occupants_are_rejected(self):
        source=self.source('or-upper')
        rows=[r.make(source,'OR','upper','Person '+str(i),str(i),'id'+str(i))for i in range(30)]
        rows[-1]['district']=rows[0]['district']
        with self.assertRaisesRegex(AssertionError,'Conflicting occupants'):
            r.checked(rows,'OR','upper')

    def test_rhode_island_active_flag_excludes_historical_entries(self):
        raw=self.ri_page('Senate','1','No')
        self.assertEqual(r.parse('ri-roster',raw,self.source('ri-roster')),[])

    def test_rhode_island_collector_follows_next_page_and_references_each_response(self):
        calls=[]
        def fetch(key,publisher,url,offline=False):
            calls.append(url)
            raw=self.ri_page('Senate','1',next_page=True)if len(calls)==1 else self.ri_page('House','2')
            return raw,dict(id=key,name=publisher,url=url)
        with patch.dict(r.SOURCES,{'ri-roster':r.SOURCES['ri-roster']},clear=True),patch.dict(r.LIMITS,{'RI':(1,1)}):
            rows,sources=r.collect(fetch)
        self.assertEqual(len(calls),2)
        self.assertEqual(len(rows),2)
        self.assertNotEqual(rows[0]['sources'][0]['url'],rows[1]['sources'][0]['url'])
        self.assertEqual(len(sources),2)


    def test_wisconsin_card_contacts_and_publisher_id(self):
        card='''<p>2025 Wisconsin State Senate</p><div id="district28">
        <img class="picture" src="https://docs.legis.wisconsin.gov/2025/legislators/senate/2805.jpg" />
        <strong><a href="https://legis.wisconsin.gov/senate/28/bradley">Bradley, Julian</a></strong> <small>(R - New Berlin)</small>
        <a href="/2025/legislators/senate/2805">Details</a>
        <span class='info telephone'>(608) 266-5400<br/>(888) 534-0064</span>
        <span class='info email'><a href="mailto:Sen.Bradley@legis.wisconsin.gov">x</a></span>
        <span class='info staff'><a href="mailto:Staff.Person@legis.wisconsin.gov">y</a></span></div>'''
        with patch.dict(r.LIMITS,{'WI':(1,99)}):
            row,=r.parse('wi-upper',card.encode(),self.source('wi-upper'))
        self.assertEqual((row['email'],row['phone'],row['ids']),('sen.bradley@legis.wisconsin.gov','608-266-5400',{'wi-upper':'2805'}))
        self.assertEqual(row['photo'],'https://docs.legis.wisconsin.gov/2025/legislators/senate/2805.jpg')

    def test_virginia_capitol_phone_is_label_anchored(self):
        card='''<p>Members of the 2026 Virginia House of Delegates</p><div class="delegate-card">
        <img src="/delegate_photos/thumbs/H0386.jpg"><a href="/members/H0386">Anderson, Jessica L.</a>
        <p>District: 71</p><p>District Phone: (757) 707-1673</p><p>Email: <a href="mailto:DelJAnderson@house.virginia.gov">e</a></p></div>'''
        with patch.dict(r.LIMITS,{'VA':(40,1)}):
            row,=r.parse('va-lower',card.encode(),self.source('va-lower'))
        self.assertNotIn('phone',row)  # district office number is not a capitol line
        self.assertEqual((row['email'],row['ids'],row['photo']),('deljanderson@house.virginia.gov',{'va-lower':'H0386'},'https://house.vga.virginia.gov/delegate_photos/thumbs/H0386.jpg'))

    def test_oregon_party_joins_only_exact_chamber_district_name(self):
        source=self.source('or-upper')
        rows=[r.make(source,'OR','upper','Dick Anderson','5','a'),r.make(source,'OR','upper','Sara Gelser Blouin','8','b')]
        api=dict(value=[dict(SessionKey='2025I1',Chamber='S',DistrictNumber='5',FirstName='Dick',LastName='Anderson',Party='Republican',LegislatorCode='Sen Anderson'),
                        dict(SessionKey='2025I1',Chamber='S',DistrictNumber='8',FirstName='Sara',LastName='Gelser',Party='Democrat',LegislatorCode='Sen Gelser')])
        r.join_oregon(rows,json.dumps(api).encode(),self.source('or-legislators'))
        self.assertEqual(rows[0]['party'],'Republican')
        self.assertEqual(rows[0]['fieldEvidence']['party'],{'value':'Republican','sourceIds':['or-legislators']})
        self.assertEqual([s['id']for s in rows[0]['sources']],['or-upper','or-legislators'])
        self.assertNotIn('party',rows[1])
        self.assertEqual(rows[1]['sources'],[source])

    def test_washington_contacts_require_current_chamber(self):
        source=self.source('wa-roster')
        row=r.make(source,'WA','upper','Emily Alvarado','34','34024',ids='34024')
        xml='''<ArrayOfMember xmlns="http://WSLWebServices.leg.wa.gov/">
        <Member><Id>34024</Id><Agency>House</Agency><District>34</District><Phone>(360) 786-7978</Phone><Email>Emily.Alvarado@leg.wa.gov</Email></Member>
        <Member><Id>34024</Id><Agency>Senate</Agency><District>34</District><Phone>(360) 786-7667</Phone><Email>Emily.Alvarado@leg.wa.gov</Email></Member></ArrayOfMember>'''
        r.join_washington([row],xml.encode(),self.source('wa-sponsors'))
        self.assertEqual(row['phone'],'360-786-7667')
        self.assertEqual(row['fieldEvidence']['email'],{'value':'emily.alvarado@leg.wa.gov','sourceIds':['wa-sponsors']})

    def test_photo_shown_for_several_people_is_dropped(self):
        def fetch(key,publisher,url,offline=False):
            people=[dict(legID=i,name='Person '+str(i),chamber='S',district='S'+str(i),legStatus='C',party='R',eMail='',phone='',
                         legPhoto='LegislatorSummary/Photos/'+('blank.jpg' if i<3 else str(i)+'.jpg'))for i in range(1,32)]
            return json.dumps(people).encode(),dict(id=key,name=publisher,url=url)
        with patch.dict(r.SOURCES,{'wy-upper':r.SOURCES['wy-upper']},clear=True):
            rows,_=r.collect(fetch)
        self.assertEqual(sum('photo' in row for row in rows),29)
        self.assertEqual(rows[4]['photo'],'https://wyoleg.gov/LegislatorSummary/Photos/5.jpg')


    def test_wyoming_member_elect_listed_current_is_excluded_by_own_record(self):
        people=[dict(legID=i,name='Person '+str(i),chamber='S',district='S'+str(i),legStatus='C',party='R',eMail='',phone='',legPhoto='')for i in range(1,32)]
        people.append(dict(people[10],legID=99,name='Member Elect'))
        records={11:{'legID':11,'currentDistrict':'S11','senateYears':'Senate: 2011-2026','houseYears':''},
                 99:{'legID':99,'currentDistrict':'S11','senateYears':'Senate: 2027-Present','houseYears':'House:  2023-2026'}}
        def fetch(key,publisher,url,offline=False):
            if url.rsplit('/',1)[1].isdigit():return json.dumps(records[int(url.rsplit('/',1)[1])]).encode(),dict(id=key,name=publisher,url=url)
            return json.dumps(people).encode(),dict(id=key,name=publisher,url=url,retrievedAt='2026-11-09T00:00:00+00:00')
        with patch.dict(r.SOURCES,{'wy-upper':r.SOURCES['wy-upper']},clear=True):
            rows,sources=r.collect(fetch)
        self.assertEqual(len(rows),31)
        self.assertEqual([x['name'] for x in rows if x['district']=='11'],['Person 11'])
        self.assertEqual(sources[-1]['excludedEntries'][0]['legID'],99)
        records[11]['senateYears']='Senate: 2027-Present'  # neither serving: the duplicate stays and the build stops
        with patch.dict(r.SOURCES,{'wy-upper':r.SOURCES['wy-upper']},clear=True),self.assertRaises(AssertionError):
            r.collect(fetch)

    @staticmethod
    def tx_page(name, party='Republican'):
        return ('<img id="memhead" src="x.jpg" alt="'+name+'"><div class="meminfo">'
                '<p class="meminfo"><span>Hometown:</span> Mineola</p>'
                '<p class="meminfo"><span>Party:</span> '+party+'</p></div>').encode()

    def test_texas_senate_party_requires_same_named_member_page(self):
        row=r.make(self.source('tx-upper'),'TX','upper','Bryan  Hughes','1','member.php?d=1')
        page={'id':'tx-upper-member-d1','url':r.TX_PAGES['tx-upper-member-d1'][1]}
        r.join_texas_senate(row,self.tx_page('Someone Else'),page)
        self.assertNotIn('party',row)
        r.join_texas_senate(row,self.tx_page('Bryan Hughes','Democrat'),page)
        self.assertEqual(row['fieldEvidence']['party'],{'value':'Democratic','sourceIds':['tx-upper-member-d1']})
        self.assertEqual(row['sources'][-1],page)

    def test_texas_senate_pages_fetched_only_for_roster_districts(self):
        calls=[]
        roster=('<p>89th Legislature</p><p>* Indicates a currently vacant seat</p>'+''.join(
            '<div class="mempicdiv"><a href="member.php?d='+str(d)+'">'+('Constituent Services *' if d==22 else 'Person '+str(d))+'</a> District '+str(d)+'</div>'
            for d in range(1,32))).encode()
        def fetch(key,publisher,url,offline=False):
            calls.append(key)
            raw=roster if key=='tx-upper' else self.tx_page('Person '+url.rsplit('=',1)[1])
            return raw,dict(id=key,name=publisher,url=url)
        with patch.dict(r.SOURCES,{'tx-upper':r.SOURCES['tx-upper'],**r.TX_PAGES},clear=True):
            rows,sources=r.collect(fetch)
        self.assertEqual(len(rows),30)
        self.assertNotIn('tx-upper-member-d22',calls)
        self.assertTrue(all(row['party']=='Republican' for row in rows))
        self.assertEqual(len(sources),31)

    def test_virginia_delegate_party_initial_only_in_search_index_position(self):
        def card(search):
            return ('<div class="delegate-card" data-search="'+search+'"><a href="/members/H0386">Anderson, Jessica L.</a>'
                    '<p>Capitol Office: 804</p><p>District: 71</p></div>')
        html=b'<p>Members of the 2026 Virginia House of Delegates</p>'
        with patch.dict(r.LIMITS,{'VA':(40,1)}):
            ok,=r.parse('va-lower',html+card('anderson, jessica l. 804 d (757) 707-1673').encode(),self.source('va-lower'))
            odd,=r.parse('va-lower',html+card('anderson, jessica l. 804 x (757) 707-1673').encode(),self.source('va-lower'))
            moved,=r.parse('va-lower',html+card('anderson, jessica l. d 804 (757) 707-1673').encode(),self.source('va-lower'))
        self.assertEqual(ok['party'],'Democratic')
        self.assertNotIn('party',odd)
        self.assertNotIn('party',moved)


if __name__=='__main__': unittest.main()
