#add (basic type) when possible for types

import xml.etree.ElementTree as ET
import xlsxwriter
from pathlib import Path

xs = "{http://www.w3.org/2001/XMLSchema}"
directory = 'fixm_schemas'

concept_list_properties = []
concept_list_containers = []

namespaces_dictionary={}

xsd_basic_types = {
    "xs:" + "string", "xs:" + "decimal", "xs:" + "integer", "xs:" + "boolean",
    "xs:" + "date", "xs:" + "time", "xs:" + "float", "xs:" + "double",
    "xs:" + "duration", "xs:" + "dateTime"
}

#******FUNCTIONS*****
#Creates excel file with the content of both concept_list_properties and concept_list_containers. Creates log.txt with same content
def concept_list_to_excel(concept_list_properties, concept_list_containers):
    workbook = xlsxwriter.Workbook('output.xlsx')
    print('Excel file created')
    f = open("log.txt", "w+")

    worksheet_properties = workbook.add_worksheet("property concepts")
    print('  *Property concepts worksheet created')
    worksheet_containers = workbook.add_worksheet("container concepts")
    print('  *Container concepts worksheet created')

    template_properties = [
        'Container', 'Name', 'Definition', 'identifier', 'Type', 'URN',
        'Context URN', 'Reason', 'Basic Type', 'Notes'
    ]
    template_containers = [
        'Name', 'Definition', 'identifier', 'Base', 'URN', 'Context URN',
        'Reason', 'Basic Type', 'Notes'
    ]
    worksheet_properties.write_row('A1', tuple(template_properties))
    worksheet_containers.write_row('A1', tuple(template_containers))
    print('  *Templates applied')

    #Concepts are inserted in excel rows starting from row number 2
    properties_index = 2
    containers_index = 2

    for element in concept_list_containers:
        result = worksheet_containers.write_row('A' + str(containers_index), tuple(element))
        containers_index += 1

        if result != 0:
            print('Error while inserting a row: ', result)
        
        #Concepts are inserted in log.txt to ease debugging
        f.write('Container :')
        f.write(repr(element))
        f.write('\n\n')
        
    for element in concept_list_properties:
        worksheet_properties.write_row('A' + str(properties_index), tuple(element))
        properties_index += 1
        
        if result != 0:
            print('Error while inserting a row: ', result)
        
        f.write('Property :')
        f.write(repr(element))
        f.write('\n\n')
        
    print('  *Properties inserted: ', properties_index - 2)
    print('  *Containers inserted: ', containers_index - 2)

    f.close()
    print('  *File closed with message: ', workbook.close())


#Recursive function. Finds container concepts and adds them to the concept_list
def process_element_container(element, namespace):
    concept = []
    concept_list_containers = []
    container_base = ''
    if element.attrib.get("name"):
        name = element.attrib.get("name")
        if element.attrib.get("type"):
            pass
        else:
            definition = 'unknown'
            for child in element:
                if child.tag == xs + 'annotation':
                    for subchild in child:
                        if subchild.tag == xs + 'documentation':
                            definition = subchild.text
                if child.tag == xs + 'restriction':
                    container_base = child.attrib.get("base")
            if namespace in namespaces_dictionary:
              identifier = namespaces_dictionary[namespace] + ":" + name
            else:
              identifier = namespace + ":" + name
            if container_base in xsd_basic_types:
                pass
                #TO-DO add id and base to dictionary for post-processing
                #TO-DO add id to initial set for managing the postprocessing
            concept = [name, definition, identifier, container_base]
            concept_list_containers.append(concept)

            for child in element:
                #Recursive call for children. Appends the results to concept_list
                concept_list_containers.extend(
                    process_element_container(child, namespace))
    else:
        for child in element:
            #Recursive call for children. Appends the results to concept_list
            concept_list_containers.extend(
                process_element_container(child, namespace))

    return concept_list_containers


#Recursive function. Finds property concepts and adds them to the concept_list
def process_element_properties(element, parent_name, namespace):
    concept = []
    concept_list_properties = []
    if element.attrib.get("name"):
        name = element.attrib.get("name")
        definition = 'unknown'
        identifier = 'unknown'
        concept_type = 'unknown'
        for child in element:
            if child.tag == xs + 'annotation':
                for subchild in child:
                    if subchild.tag == xs + 'documentation':
                        definition = subchild.text

        if element.tag == xs + 'element' and parent_name != 'unknown':
            identifier = namespace + ":" + parent_name + ":" + name
            concept_type = element.attrib.get("type")

        elif element.tag == xs + 'attribute' and parent_name != 'unknown':
            identifier = namespace + ":" + parent_name + ":" + name
            concept_type = element.attrib.get("type")

        if concept_type != 'unknown':
            concept = [parent_name, name, definition, identifier, concept_type]
            concept_list_properties.append(concept)

        for child in element:
            #Recursive call for children. Appends the results to concept_list
            parent_name = name
            concept_list_properties.extend(
                process_element_properties(child, parent_name, namespace))

    elif element.tag == xs + 'enumeration':  #Special case: Enumeration values
        definition = 'unknown'
        name = element.attrib.get("value")
        for child in element:
            if child.tag == xs + 'annotation':
                for subchild in child:
                    if subchild.tag == xs + 'documentation':
                        definition = subchild.text

        identifier = namespace + ":" + parent_name + ":" + name

        concept_type = 'enum value'
        concept = [parent_name, name, definition, identifier, concept_type]

        concept_list_properties.append(concept)

        for child in element:
            #Recursive call for children. Appends the results to concept_list
            parent_name = name
            concept_list_properties.extend(
                process_element_properties(child, parent_name, namespace))

    else:
        for child in element:
            #Recursive call for children. Appends the results to concept_list
            concept_list_properties.extend(
                process_element_properties(child, parent_name, namespace))

    return concept_list_properties


#*****MAIN LOGIC*****
#Find all .xsd files in a directory (and subdirectories)
print('Searching for .xsd files in directory:', directory)
for path in Path(directory).rglob('*.xsd'):
    print('  *.xsd file found: ', path)
    #Add namespaces to dictionary
    namespaces_dictionary.update(dict([node for _, node in ET.iterparse(path, events=['start-ns'])]))
    my_inverted_dict = dict(map(reversed, namespaces_dictionary.items()))
    namespaces_dictionary = my_inverted_dict
    
    tree = ET.parse(path)
    root = tree.getroot()
    namespace = root.attrib.get("targetNamespace")

    for child in root:
        concept_list_properties.extend(
            process_element_properties(child, "unknown", namespace))
        concept_list_containers.extend(
            process_element_container(child, namespace))
print('  *No more files to process')


#Build initial base set
base_set = set()
for concept in concept_list_containers:
  if concept[3] in xsd_basic_types: #concept_list_containers[3]: Base type
    base_set.add(concept[3])
print("base_set: ")
print(base_set)

base_dictionary={}
while base_set!={}:
  new_base_set = set()
  for concept in concept_list_containers:
    if concept[3] in base_set: #concept_list_containers[3]: Base type
      new_base_set.add(concept[2]) #concept_list_containers[2]: identifier
      base_dictionary[concept[2]] = concept[3]
      print("base_dictionary updated: ")
      print(base_dictionary)
  base_set = new_base_set
print("base_dictionary complete: ")
print(base_dictionary)

#TO-DO Create dictionary of base types starting from initial set built in process_element_container
#TO-DO Post-process both concept_list using dictionary of base types

#create excel file with results
concept_list_to_excel(concept_list_properties, concept_list_containers)

print("DONE. Download as a zip and open output.xlsx")
