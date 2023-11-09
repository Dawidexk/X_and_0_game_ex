#!/usr/bin/python3

import os.path
import xml.etree.ElementTree
from urllib.parse import urljoin
import sys
import re
import json

origin = 'buic-scm:'
fermi_org = 'fermi'
opensource_org = 'opensource'
mirror_fermi = 'ssh://git@git-id-test0.conti.de/' + fermi_org
mirror_opensource = 'ssh://git@git-id-test0.conti.de/' + opensource_org

repository_file = '.\\repositories.json'

remote = {}
default_remote = None
modify_list = True

mapping = {}

if os.path.isfile('default.xml'):

    try:
        tree = xml.etree.ElementTree.parse('default.xml')
    except:
        print('Error in parsing default.xml')
        exit(0)

    repository_list = json.load(open(repository_file, 'r'))

    #<remote fetch="ssh://git@git-id-test0.conti.de/g-tp-opensource" name="opensource"/>
    xmlRoot = tree.getroot()
    new_child = xml.etree.ElementTree.Element('remote',{'fetch':mirror_opensource, 'name':'opensource'})
    xmlRoot.insert(1,new_child)

    xml.etree.ElementTree.indent(xmlRoot, '')
        
    for child in xmlRoot:

        
        # patch fetch
        if child.tag == 'remote':

            # fetch=".." -> fetch="ssh://git@git-id.conti.de/iip-android"
            remote[child.attrib.get('name')] = origin
            if child.attrib.get('fetch') != mirror_opensource:
                remote[child.attrib.get('name')] = urljoin(remote[child.attrib.get('name')], child.attrib.get('fetch'))
                child.set('fetch', mirror_fermi)
            if child.attrib.get('review'):
                child.attrib.pop('review', None)

        # process default remote
        if child.tag == 'default':
            if child.attrib.get('remote'):
                default_remote = remote[child.attrib.get('remote')]

        # patch repo-hooks:
        if child.tag == 'repo-hooks':
            project = child.attrib.get('in-project')
            project = re.sub('/', '.', project)
            child.set('in-project', project)

        # patch project
        if child.tag == 'project':
            origin_name = child.attrib.get('name')
            add_remote = re.search('opensource',origin_name)
            if(add_remote):
                child.attrib['remote'] = 'opensource'
            
            
            # patch revision
            # commit id     <commit-id>         -> old-ref-<commit-id>
            # tag           refs/tags/<tag>     -> old-ref-<tag>
            if child.attrib.get('revision'):
                revision = child.attrib.get('revision')
                if re.search('[0-9A-Fa-f]{40}', revision):
                    revision = re.split('/',revision)
                    revision = 'refs/tags/old-ref-' + revision[-1]
                    child.set('revision', revision)

            # add patch if missing: path="device/common"
            if not child.attrib.get('path'):
                child.set('path', origin_name)

            # remove clone-depth
            if child.attrib.get('clone-depth'):
                child.attrib.pop('clone-depth', None)

            # ensure naming length
            if origin_name in mapping:
                name = mapping[origin_name]
            else:
                name = origin_name

            # modify repository checkout name: name="device/common" -> name="device.common"
            mirror_name = re.sub('/', '.', name)
            child.set('name', mirror_name)

            # get full repository name
            if child.attrib.get('remote'):
                #print(remote[child.attrib.get('remote')])
                origin_repository = urljoin(remote[child.attrib.get('remote')], origin_name)
            else:
                origin_repository = urljoin(default_remote, origin_name)

            # write list
            if origin_name not in repository_list:
                repository_list[origin_name] = {
                    'origin': origin_repository,
                    'mirror': {
                        'url': mirror_fermi + '/' + mirror_name + '.git',
                        'organization': fermi_org,
                        'repository': mirror_name
                    }
                }
                modify_list = True

    tree.write('default.xml', encoding='UTF-8', xml_declaration=True)
    if modify_list:
        open(repository_file, 'w+').write(json.dumps(repository_list, indent=2))
