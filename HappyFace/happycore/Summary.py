from ModuleBase import *
from DownloadTag import *
from XMLParsing import *


class Summary(ModuleBase):

    def __init__(self, module_options):
	ModuleBase.__init__(self, module_options)

	# definition of the database table keys and pre-defined values

	self.db_keys["summary_database"] = StringCol()
	self.db_values["summary_database"] = ""

        self.configService.addToParameter('setup','definition','Monitors multiple HappyFace instances')

	self.dsTags = {}
	sites = self.configService.getSection('Sites')

	first_iteration = True
	for site in sites.keys():
	    dsTag = 'summary_xml_source_' + site
	    url = sites[site] + "?action=getxml"

	    self.dsTags[dsTag] = {}
	    self.dsTags[dsTag]['site'] = site
	    self.downloadRequest[dsTag] = 'wget|xml||' + url

        self.categories = self.configService.get('setup','categories').split(",")
	if self.categories == ['']:
		self.categories = []

    def run(self):

	# Database setup
	summary_database = self.__module__ + "_table_summary"
	self.db_values["summary_database"] = summary_database

	summary_db_keys = {}
	summary_db_values = {}

	summary_db_keys["site"] = StringCol()
	summary_db_keys["catname"] = StringCol()
	summary_db_keys["cattitle"] = StringCol()
	summary_db_keys["type"] = StringCol()
	summary_db_keys["status"] = FloatCol()
	summary_db_keys["link"] = StringCol()

	# Remember the keys we are supposed to set to check that we do
	# set them later
	my_keys = []
	for key in summary_db_keys:
	    my_keys.append(key)

	# Own status is worst of all category statusses of all sites
	self.status = 1.0

	subtable_summary = self.table_init(self.db_values["summary_database"], summary_db_keys)

	try:
	    first_iteration = True
	    for tag in self.dsTags.keys():
	        site = self.dsTags[tag]['site']
	        if not first_iteration:
	            self.configService.addToParameter('setup', 'source', '<br />')
	        first_iteration = False

	        self.configService.addToParameter('setup', 'source', site + ': ' + self.downloadService.getUrlAsLink(self.downloadRequest[tag]))

	        if not tag in self.downloadRequest:
		    raise Exception('Error: Could not find required tag: ' + tag)

	        dl_error,sourceFile = self.downloadService.getFile(self.downloadRequest[tag])
	        if dl_error != "":
		    raise Exception(dl_error)

	        source_tree,xml_error = XMLParsing().parse_xmlfile_lxml(sourceFile)
		if source_tree == "":
		    raise Exception(xml_error)

	        root = source_tree.getroot()
	        summary_db_values["site"] = site

	        for element in root:
		    if element.tag == "category":
		        mod_status = -1.0
			have_category = False
		        for cat_elem in element:
		            if cat_elem.tag == "name":
			        # Check whether to include this category in summary
			    	if len(self.categories) == 0 or cat_elem.text in self.categories:
				    have_category = True
				else:
				    break # Don't waste time

			        summary_db_values["catname"] = cat_elem.text
			    elif cat_elem.tag == "title":
			        summary_db_values["cattitle"] = cat_elem.text
			    elif cat_elem.tag == "type":
			        summary_db_values["type"] = cat_elem.text

			        # Provide dummy status for unrated categories so
			        # that database insertion can succeed.
			        if cat_elem.text == "unrated":
			            summary_db_values["status"] = 0.0;
			    elif cat_elem.tag == "status":
			        status = float(cat_elem.text)
			        if status >= 0.0 and status <= self.status:
			            self.status = status
			        summary_db_values["status"] = status
			    elif cat_elem.tag == "link":
			        summary_db_values["link"] = cat_elem.text
			    # Overwrite category link with link to failing
			    # module within that category, if any (for "rated"
			    # categories and modules only).
			    elif cat_elem.tag == "module" and summary_db_values["type"] == "rated":
				status = -1.0
				type = ""
				link = ""
				for mod_elem in cat_elem:
				    if mod_elem.tag == "status":
				        status = float(mod_elem.text)
				    elif mod_elem.tag == "type":
				        type = mod_elem.text
				    elif mod_elem.tag == "link":
				        link = mod_elem.text

				if type == "rated" and link != "" and status >= 0.0:
				    if mod_status < 0.0 or status < mod_status:
				        mod_status = status
					if mod_status < 1.0:
			                    summary_db_values["link"] = link

		        if have_category:
		            # Make sure we have a value for each key
		            # We can't use summary_db_keys directly here since it
		            # contains more keys than the ones we need to supply.
		            for key in my_keys:
		                if not key in summary_db_values:
			            raise Exception('XML does not provide a value for ' + key)

		            self.table_fill(subtable_summary, summary_db_values)

	except Exception as ex:
	    self.status = -1.0
	    self.error_message = "Failed to parse XML: " + str(ex)

    def output(self):

	mc_begin = []
	mc_header_row = []
	mc_header_end = []
	mc_row_begin = []
	mc_row_cell_known = []
	mc_row_cell_unknown = []
	mc_row_end = []
	mc_end = []

	mc_begin.append(           '<table class="SummaryTable">')
	mc_begin.append(           ' <tr class="TableHeader">')
	mc_begin.append(           '  <td class="SummaryCatHeader">Site</td>')
	mc_header_row.append(    """  <td class="SummaryCatHeader">' . $catinfo['title'] . '</td>""")
	mc_header_end.append(      ' </tr>')
	mc_row_begin.append(     """ <tr class="' . $status_class . '">""")
	mc_row_begin.append(     """  <td class="SummarySite">' . $site . '</td>""")
	mc_row_cell_known.append("""  <td class="SummaryCatCell"><a href="' . htmlentities($siteinfo[$category]['link']) . '">' . getCatStatusSymbol($categories[$category]['type'], $siteinfo[$category]['status'], 'SummaryCatIcon') . '</a></td>""")
	mc_row_cell_unknown.append('  <td class="SummaryCatCell">N/A</td>')
	mc_row_end.append(         ' </tr>')
	mc_end.append(             '</table>')

	module_content = """<?php

	$summary_db_sqlquery = "SELECT * FROM " . $data["summary_database"] . " WHERE timestamp = " . $data["timestamp"];

	foreach($dbh->query($summary_db_sqlquery) as $info)   
	{
	    if($info['type'] == 'rated' && $info['status'] >= 0.0)
	    {
	        if(!isset($sites[$info['site']]['status']))
	            $sites[$info['site']]['status'] = $info['status'];
	        elseif($info['status'] < $sites[$info['site']]['status'])
	            $sites[$info['site']]['status'] = $info['status'];
	    }

	    $sites[$info['site']][$info['catname']]['status'] = $info['status'];
	    $sites[$info['site']][$info['catname']]['link'] = $info['link'];
	    $categories[$info['catname']]['title'] = $info['cattitle'];
	    $categories[$info['catname']]['type'] = $info['type'];
	}

	print('""" + self.PHPArrayToString(mc_begin) + """');

	foreach($categories as $category=>$catinfo)
	{
	    print('""" + self.PHPArrayToString(mc_header_row) + """');
	}

	print('""" + self.PHPArrayToString(mc_header_end) + """');

	foreach($sites as $site=>$siteinfo)
	{
	    // Don't set background color by worst category status...
	    // does not look as good as I hoped it would.
	    /*
	    if(isset($sites[$info['site']]['status']))
	    {
	        if($sites[$info['site']]['status'] >= 0.66)
	            $status_class = "ok";
	        elseif($sites[$info['site']]['status'] >= 0.33 && $sites[$info['site']]['status'] <= 0.66)
	            $status_class = "warning";
	        else
	            $status_class = "critical";
	    }
	    else*/
	        $status_class = "undefined";

	    print('""" + self.PHPArrayToString(mc_row_begin) + """');

	    foreach($categories as $category=>$catinfo)
	    {
	        if(isset($siteinfo[$category]))
	            print('""" + self.PHPArrayToString(mc_row_cell_known) + """');
		else
	            print('""" + self.PHPArrayToString(mc_row_cell_unknown) + """');
	    }

	    print('""" + self.PHPArrayToString(mc_row_end) + """');
	}

	print('""" + self.PHPArrayToString(mc_end) + """');

	?>"""

	return self.PHPOutput(module_content)