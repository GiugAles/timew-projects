#!/usr/bin/env python3
import sys
import hashlib

from timewreport.parser import TimeWarriorParser
from tabulate import tabulate



###
# This will sum up project times depending on a hierarchy
# The hierarchy might be defined as follows:
#    theme.colors.exclusion: gray8 on gray4
#    reports.project.<tag-super-name>: <tag-sub-name-1> <tag-sub-name-2>
#    reports.project.CLab: CEIS editorial
#    reports.struct-tag.CEIS.parent = CLab
# hint: tag-tree did not work as expected
#
# Free Energy Principle, Literature Research, PhD 
#
#  PhD
#  |- Literature Research
#     |- Free Energy Principle
#
###
class ProjectNode():
    
    _name = ""
    _parent = None
    _parent_id = None
    _time = 0
    _id = ""

    def __init__(self,name: str, parent_name: str = "") -> None:
        self._name = name
        self._parent = parent_name
        self._id = self._generate_id(name, parent_name)
    
    def _generate_id(self, node_name, parent_name):
        combined_string = node_name + parent_name
        
        # Hash the combined string using SHA-256
        hash_object = hashlib.sha256(combined_string.encode())
        
        # Get the hexadecimal representation of the hash
        hex_digest = hash_object.hexdigest()
        
        # Return the hexadecimal representation as the unique ID
        return hex_digest

def load_structure(config) -> list:
    if not getattr(config, "reports.tagstructure.hierarchy.1"):
        raise RuntimeError("This extension requires at least one hierarchy level")
    structure = []
    for i in range(1,1):
        # structure.append(config[f"reports.tagstructure.hierarchy.{i}"].split("\w"))
        pass
    
    return structure

def _table_from_activities(data, structured_activities):
    # Since the activities are unordered and ordering happens by parent ids,
    # it seemed easier to have the parent ids in lists. Hence the data is structured
    # column-wise
    max_level = max(act[1] for act in structured_activities.values())
    # Initialize empty cols    
    cols = [[] for i in range(max_level + 1)]

    # Fill rows with activity names at their respective hierarchy levels
    filled_rows = 0
    for activity_id, (group, level) in structured_activities.items():
        activity = data[activity_id]

        if not activity._parent_id:
            for col in cols:
                col.insert(filled_rows + 1,"")
            cols[0][filled_rows] = activity_id
            cols[-1][filled_rows] = activity._time
        else:
            # The children go in the col next to their parents
            parent_row = cols[structured_activities[activity_id][1] - 1].index(activity._parent_id)
            parent_col = structured_activities[activity._parent_id][1]
            for col in cols:
                col.insert(parent_row + 1,"")
            cols[level][1 + parent_row] = activity_id
            cols[-1][1 + parent_row] = activity._time

        filled_rows += 1
    
    return cols

def _structure_activities(data):
    structured_activities = {}
    # structure_activities = {
    #     "ID(CLab)": [group_idx, level],
    #     "ID(CLab)": [0, 0],
    #     "ID(CEIS)": [0, 1],
    #     "ID(Draft)": [0, 2],
    #     "ID(Mock)": [0, 2],
    #     "ID(zfst_proposal)": [1, 0],
    # }
    def recursive(node, group_idx):
        level = 0
        id = node._id

        if node._parent_id:
            # not a parent. go deeper.
            group_idx, level = recursive(data[node._parent_id],group_idx)
            level += 1
        else:
            if not id in structured_activities:
                if 0 < len(structured_activities):
                    group_idx = 1 + max(act[0] for act in structured_activities.values())
                else:
                    group_idx = 0
            else:
                group_idx = structured_activities[id][0]
            level = 0

        if id not in structured_activities:
            structured_activities.update({id: [group_idx,level]})


        return group_idx, level

    group_idx = -1
    for node in data.values():
        if node._id in structured_activities:
            # not has already been seen
            continue
        group_idx, level = recursive(node, group_idx)

    return structured_activities

def create_nodes_from_tags(tags, nodes, time):
    # Precautions if interval is not tagged
    node_name = "untagged" if 0 == len(tags) else tags.pop()
    node = ProjectNode(node_name, "" if 0 == len(tags) else tags[-1])
    
    if not node._id in nodes.keys():
        nodes.update({node._id: node})
        nodes[node._id]._time = time
    else:
        nodes[node._id]._time += time
    
    if 0 < len(tags):
        nodes[node._id]._parent_id  = create_nodes_from_tags(tags,nodes,time)
    
    return node._id

def visualize(data):
    #Build a matrix for activity id (since unique) and hierarchy level.
    structured_activities = _structure_activities(data)

    # _structure_activities provides information about grouping and the depth of an activity
    # but they must be grouped and tabalized to be visualized
    cols = _table_from_activities(data,structured_activities)

    max_level = max(act[1] for act in structured_activities.values())
    
    # To prevent disambiguity, data is grouped using ids. Hence, transpose and replace
    rows = [[''] * (max_level + 1) for _ in range(len(data))]
    for col_num in range(len(cols)):
        for row_num in range(len(rows)):
            if cols[col_num][row_num]:
                rows[row_num][col_num] = data[cols[col_num][row_num]]._name if col_num < max_level else cols[col_num][row_num]
            else:
                rows[row_num][col_num] = ""

    # Print the table
    headers = [f'Level {level}' for level in range(max_level + 1)] + ['Duration']
    print(tabulate(rows, headers=headers, tablefmt='grid'))

    return structured_activities


def sort_tags_by_prio(interval, priorities):
    priorized_tags = {}
    
    for tag in interval.get_tags():
        priorized_tags.update({tag: 1 + len(priorities)})
        i = 1 # starting with 1 since there is no prio 0 - does this make sense for the code, though?
        for prio in priorities:
            if tag in prio and i < priorized_tags[tag]:
                    priorized_tags.update({tag: i})
            i += 1
    
    priorized_tags = dict(sorted(priorized_tags.items(), key=lambda item: item[1]))

    return priorized_tags


def main():
    parser = TimeWarriorParser(sys.stdin)   

    config = parser.get_config()
    
    # Crate a list of activities. An activity is an interval with tag that is not defined in the hierarchy
    # It has a parent that is an interval with tag that is defined in the hierarchy

    priorities = [
        ["CLab", "PhD", "Interactions", "zsft proposal", "WISER", "Teaching"],
        ["CEIS", "Editorial", "Literature Research", "Meeting", "CN", "Self-management"],
        ["A1", "A2", "A3"],
        ["prep", "eval","meeting"],
    ]
    
    nodes = {}
    for interval in parser.get_intervals():
        # tags are sorted alphanumerically, not by priority
        priorized_tags = sort_tags_by_prio(interval, priorities)
        # calculate time
        time = interval.get_duration().total_seconds()/3600
        # A node is identified by a set of tags. Each subset of the tags is a node itself
        # E.g. (Teaching, Course1) contributes to the nodes Teaching and Course1
        # and (Teaching, Course2) contributes to the nodes Teaching and Course2
        create_nodes_from_tags(list(priorized_tags.keys()),nodes,time)
    
    visualize(nodes)

if __name__ == "__main__":
    main()