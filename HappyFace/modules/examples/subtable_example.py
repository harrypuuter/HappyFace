from ModuleBase import *

class subtable_example(ModuleBase):

    def __init__(self,module_options):

        # inherits from the ModuleBase Class
        ModuleBase.__init__(self,module_options)

        # read additional config settings
	self.max_number = self.configService.get('setup','max_number')

	# title of the subtable has to be lowercased!!!
	# of course it is possible to create more than one subtable if necessary
        self.db_keys["subtable"] = StringCol()
        self.db_values["subtable"] = self.__module__ + "_whatever_subtable"
	
    def process(self):

	# definition of the dictionaries for the subtable
	sub_keys = {}

	# possible data types are IntCol, FloatCol, StringCol
	sub_keys["number"] = IntCol()
	sub_keys["square"] = IntCol()
	sub_keys["square_root"] = FloatCol()
	
	# ===================================================================================
	# initialisation of the table class with "table_init"(name_of_the_table, table_keys)
	# an addition of new columns (keys) into existing tables is now possible
	my_subtable_class = self.table_init( self.db_values["subtable"], sub_keys )
	# ===================================================================================
	
	sub_values_list = []
	# for loop for multiple table filling with the same timestamp
	for i in range( 0, int(self.max_number) ):
	    sub_values = {}
	    sub_values["number"] = i
	    sub_values["square"] = i*i
	    sub_values["square_root"] = float(i)**(1/2.0)
	    sub_values_list.append(sub_values)
	    
	# ===============================================================================
	# fill the table with values; "table_fill_many"(created_table_class, list_of_table_values)
	# the timestamp will automatically be saved as an non-unique primary index
	# for the later sql query in the php fragment
	# beware that the names of keys and values are consistent
        self.table_fill_many(my_subtable_class, sub_values_list)
	# ===============================================================================
	    

	# there is also a clearing algorith to erase old data
	# the second parameter specifies a list of columns containing filenames
	# which should be deleted
	# the third int value defines the holdback time in days
	# normally this should be the default holdback time configured in the
	# main HappyFace configuration which is accessible by
	# self.holdback_time
	self.table_clear( my_subtable_class, [], self.holdback_time)
	    
        # define module status 0.0..1.0 or -1 for error
        self.status = 1.0 # always happy

    def output(self):

        # create output string, all data stored in the module specific table is available via a $data[key] call
        module_content = """
	<?php
		# ===========================================================================
		# definition of the sql query for the subtable (depending on the saved script running timestamp)
		$my_sqlquery = "SELECT * FROM " . $data["subtable"] . " WHERE timestamp = " . $data["timestamp"];
		
		print('<table width="480" border="1">');
		print('<tr><td>number</td><td>square</td><td>square root</td></tr>');
		
		# ===========================================================================
		# table access with a foreach loop and the created sql query
		foreach ($dbh->query($my_sqlquery) as $sub_data)
		{
			print('
				<tr><td>' . $sub_data["number"] . "</td><td> " . $sub_data["square"] . "</td><td>" . $sub_data["square_root"] . '</td><tr>
			');
		}
		print('</table>');
	?>
	"""

        return self.PHPOutput(module_content)