from . import orm
from .config import config
from time import time
import sys, math, paramiko
from pprint import pprint

def init():
    if 'ssh' in config['src']:
        print("initializing ssh connection with src")
        ssh = paramiko.SSHClient() 
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            ssh.connect(config['src']['ssh']['host'],
                        username=config['src']['ssh']['user'],
                        password=config['src']['ssh']['pass'])
        except paramiko.ssh_exception.AuthenticationException:
            print("ssh authentication to src failed.")
            sys.exit(1)
        sftp = ssh.open_sftp()
    else:
        ssh = None
        sftp = None
    print("initializing migration process")
    return orm.init(), ssh, sftp

def close(cn):
    print("closing connection with databases")
    orm.close(cn)
    if ssh:
        print("closing ssh connection with remote")
        sftp.close()
        ssh.close()

def run(project_identifier):
    project_obj = orm.findone(cn['src'], 'projects', {
        'identifier': project_identifier
    })
    if not project_obj:
        return False
    instance()
    project(project_obj)
    close(cn)
    return True

cn, ssh, sftp = init()

ENTITY = 0
AFFECTED = 1

FUNC = 0
TYPE = 0
TABLE = 1
COLUMN = 1
SRC = 2
POLYMORPH = 2
DST = 3
MODEL = 3


# wow much comprehensible function
def fetch(table, data, o2m={}, m2o={}, m2m={},
        polymorphic={}, stub=[], translate={}, pkey='id'):
    if data is None:
        return None, False
    dst = orm.findone(cn['dst'], table, {pkey: data[pkey]})
    if dst: return dst, False
    dst = dict(data)
    for s in stub:
        dst.pop(s, None)
    for _from, _func in translate.items():
        if _from not in data:
            dst[_from] = _func(data)
    orm.insert(cn['dst'], table, dst)
    for _table, scheme in m2m.items():
        for join in orm.find(cn['src'], _table, {scheme[SRC]: dst['id']}):
            if orm.findone(cn['dst'], _table, join): continue
            rel = scheme[FUNC](orm.findone(cn['src'], scheme[TABLE], {
                'id': join[scheme[DST]]}))
            orm.insert(cn['dst'], _table, {
                scheme[SRC]: dst['id'], scheme[DST]: rel['id']})
    for column, scheme in m2o.items():
        if not data[column]:
            continue
        scheme[FUNC](orm.findone(
            cn['src'], scheme[TABLE], {pkey: dst[column]}
        ))
    for _table, scheme in o2m.items():
        if _table[:1] == '_':
            __table = _table[1:]
            for _scheme in scheme:
                filters = {_scheme[COLUMN]: dst[pkey]}
                if len(scheme) == 4:
                    filters[scheme[POLYMORPH]] = scheme[MODEL]
                for p in orm.find(cn['src'], __table, filters):
                    _scheme[FUNC](p)
        else:
            filters = {scheme[COLUMN]: dst[pkey]}
            if len(scheme) == 4:
                filters[scheme[POLYMORPH]] = scheme[MODEL]
            for p in orm.find(cn['src'], _table, filters):
                scheme[FUNC](p)
    for poly_id_field, scheme in polymorphic.items():
        _scheme = scheme[COLUMN][data[scheme[TYPE]]]
        _scheme[FUNC](orm.findone(
            cn['src'], _scheme[TABLE], {pkey: dst[poly_id_field]}
        ))
    return dst, True

##################################################

def instance():
    print("importing global instance structure")
    pkeys()
    for s in orm.find(cn['src'], 'settings'):
        setting(s)
    for s in orm.find(cn['src'], 'issue_statuses'):
        issue_status(s)
    for t in orm.find(cn['src'], 'trackers'):
        tracker(t)
    for w in orm.find(cn['src'], 'workflows'):
        workflow(w)
    for p in orm.find(cn['src'], 'enumerations', {
            'type': 'IssuePriority', 'project_id': None}):
        issue_priority(p)
    for a in orm.find(cn['src'], 'enumerations', {
            'type': 'TimeEntryActivity', 'project_id': None}):
        activity(a)
    for g in orm.find(cn['src'], 'users', {'type': 'Group'}):
        group(g)
    for q in orm.find(cn['src'], 'queries', {'project_id': None}):
        query(q)
    for cf in orm.find(cn['src'], 'custom_fields'):
        custom_field(cf)

def pkeys():
    status = orm.findone(cn['dst'], 'settings', {'name': 'sequences-migrated'})
    if status and int(status['value']) > 0:
        return
    print("migrating primary key sequences to safe values")
    sequences = {}
    for table in orm.fetch_tables(cn['src']):
        seq = orm.get_sequence_value(cn['src'], table)
        if not seq: continue
        sequences[table] = seq
    rel = config['relative']
    relative_value = sequences[rel['reference_table']]
    for table, seqval in sequences.items():
        newseq = int((seqval / relative_value) * rel['new_sequence'])
        if table != rel['reference_table'] and newseq < rel['new_sequence']:
            newseq = rel['new_sequence']
        orm.set_sequence_value(cn['dst'], table, newseq + 1)
    orm.insert(cn['dst'], 'settings', {
        'name': 'sequences-migrated', 'value': int(time())
    })

def project(src):
    return fetch('projects', src, stub=['customer_id'],
           o2m={
               'projects': [project, 'parent_id'],
               'issues': [issue, 'project_id'],
               'enabled_modules': [enabled_module, 'project_id'],
               'time_entries': [time_entry, 'project_id'],
               'wikis': [wiki, 'project_id'],
               'members': [member, 'project_id'],
               'boards': [board, 'project_id'],
               'documents': [document, 'project_id'],
               'news': [news, 'project_id'],
               'queries': [query, 'project_id'],
               'attachments': [
                   attachment, 'container_id', 'container_type', 'Project',
               ],
               'custom_values': [
                   custom_value, 'customized_id', 'customized_type', 'Project',
               ],
           },
           m2m={
               'custom_fields_projects': [
                   custom_field,
                   'custom_fields','project_id', 'custom_field_id'
               ],
               'projects_trackers': [
                   tracker, 'trackers', 'project_id', 'tracker_id'
               ],
           },
           m2o={'parent_id': [project, 'projects']},
    )

def issue(src):
    return fetch('issues', src, stub=[
                'story_points',
                'remaining_hours',
                'release_relationship',
                'release_id',
                'reminder_notification',
                'position',
           ],
           o2m={
               'issues': [issue, 'parent_id'],
               'custom_values': [
                   custom_value, 'customized_id', 'customized_type', 'Issue',
               ],
               '_issue_relations': [
                   [issue_relation, 'issue_from_id'],
                   [issue_relation, 'issue_to_id'],
               ],
               'journals': [
                   journal, 'journalized_id', 'journalized_type', 'Issue',
               ],
               'attachments': [
                   attachment, 'container_id', 'container_type', 'Issue',
               ],
               'watchers': [
                   watcher, 'watchable_id', 'watchable_type', 'Issue',
               ],
           },
           m2o={
               'tracker_id': [tracker, 'trackers'],
               'project_id': [project, 'projects'],
               'category_id': [issue_category, 'issue_categories'],
               'status_id': [issue_status, 'issue_statuses'],
               'assigned_to_id': [user, 'users'],
               'priority_id': [issue_priority, 'enumerations'],
               'fixed_version_id': [version, 'versions'],
               'author_id': [user, 'users'],
               'parent_id': [issue, 'issues'],
               'root_id': [issue, 'issues']
           },
    )[ENTITY]

def tracker(src):
    return fetch('trackers', src,
           m2m={
               'custom_fields_trackers': [custom_field,
                   'custom_fields', 'tracker_id', 'custom_field_id']
           }
    )[ENTITY]

def issue_category(src):
    return fetch('issue_categories', src,
           stub=['reminder_notification'],
           m2o={
              'assigned_to_id': [user, 'users'],
              'project_id': [project, 'projects']
           },
    )[ENTITY]

def issue_status(src):
    return fetch('issue_statuses', src)[ENTITY]

def user(src):
    return fetch('users', src, stub=['reminder_notification'],
           m2o={
              'auth_source_id': [auth_source, 'auth_sources'],
           },
           o2m={
              'tokens': [token, 'user_id'],
              'user_preferences': [user_preference, 'user_id'],
           },
           m2m={
               'groups_users': [group, 'users', 'user_id', 'group_id'],
           },
    )[ENTITY]

def issue_priority(src):
    return fetch('enumerations', src,
           m2o={
              'parent_id': [issue_priority, 'enumerations'],
              'project_id': [project, 'projects']
           },
    )[ENTITY]

def activity(src):
    return fetch('enumerations', src,
           m2o={
              'parent_id': [issue_priority, 'enumerations'],
              'project_id': [project, 'projects']
           },
    )[ENTITY]

def version(src):
    return fetch('versions', src,
           stub=['sprint_start_date'],
           m2o={
              'project_id': [project, 'projects']
           },
           o2m={
               'attachments': [
                   attachment, 'container_id', 'container_type', 'Version',
               ],
           }
    )[ENTITY]

def enabled_module(src):
    return fetch('enabled_modules', src,
           m2o={
              'project_id': [project, 'projects']
           },
    )[ENTITY]

def time_entry(src):
    return fetch('time_entries', src, stub=[],
           m2o={
               'project_id': [project, 'projects'],
               'user_id': [user, 'users'],
               'issue_id': [issue, 'issues'],
               'activity_id': [activity, 'enumerations'],
           },
    )[ENTITY]

def wiki(src):
    return fetch('wikis', src,
           m2o={
              'project_id': [project, 'projects'],
           },
           o2m={
               'wiki_pages': [wiki_page, 'wiki_id'],
               'wiki_redirects': [wiki_redirect, 'wiki_id'],
               'watchers': [
                   watcher, 'watchable_id', 'watchable_type', 'Wiki',
               ]
           },
    )[ENTITY]

def wiki_page(src):
    return fetch('wiki_pages', src,
           m2o={
              'wiki_id': [wiki, 'wikis'],
              'parent_id': [wiki_page, 'wiki_pages'],
           },
           o2m={
              'wiki_pages': [wiki_page, 'parent_id'],
              'wiki_contents': [wiki_content, 'page_id'],
              'attachments': [
                  attachment, 'container_id', 'container_type', 'WikiPage',
              ],
              'watchers': [
                  watcher, 'watchable_id', 'watchable_type', 'WikiPage',
              ],
           },
    )[ENTITY]

def wiki_content(src):
    return fetch('wiki_contents', src,
           m2o={
              'page_id': [wiki_page, 'wiki_pages'],
              'author_id': [user, 'users'],
           },
           o2m={
              'wiki_content_versions': [
                  wiki_content_version, 'wiki_content_id'
              ],
           },
    )[ENTITY]

def wiki_redirect(src):
    return fetch('wiki_redirects', src,
           m2o={
              'wiki_id': [wiki, 'wikis'],
           }
    )

def wiki_content_version(src):
    return fetch('wiki_content_versions', src,
           m2o={
              'wiki_content_id': [wiki_content, 'wiki_contents'],
              'page_id': [wiki_page, 'wiki_pages'],
              'author_id': [user, 'users'],
           }
    )[ENTITY]

def journal(src):
    return fetch('journals', src, stub=[],
           polymorphic={
               'journalized_id': ['journalized_type', {
                   'Issue': [issue, 'issues']
               }]
           },
           m2o={
               'user_id': [user, 'users']
           },
           o2m={
              'journal_details': [
                  journal_detail, 'journal_id'
              ],
           },
    )[ENTITY]

def journal_detail(src):
    return fetch('journal_details', src,
           m2o={
               'journal_id': [journal, 'journals']
           },
    )[ENTITY]

def auth_source(src):
    return fetch('auth_sources', src)[ENTITY]

def member_role(src):
    return fetch('member_roles', src,
           m2o={
               'member_id': [member, 'members'],
               'role_id': [role, 'roles'],
               'inherited_from': [member_role, 'member_roles'],
           },
    )[ENTITY]

def role(src):
    return fetch('roles', src)[ENTITY]

def member(src):
    return fetch('members', src,
           m2o={
               'user_id': [user, 'users'],
               'project_id': [project, 'projects'],
           },
           o2m={
              'member_roles': [
                  member_role, 'member_id'
              ],
           },
    )[ENTITY]

def board(src):
    return fetch('boards', src,
           m2o={
               'last_message_id': [message, 'messages'],
               'project_id': [project, 'projects'],
               'parent_id': [board, 'boards'],
           },
           o2m={
              'messages': [
                  message, 'board_id'
              ],
              'boards': [
                  board, 'parent_id'
              ],
              'watchers': [
                  watcher, 'watchable_id', 'watchable_type', 'Board',
              ],
           },
    )[ENTITY]

def message(src):
    return fetch('messages', src,
           m2o={
               'board_id': [board, 'boards'],
               'parent_id': [message, 'messages'],
               'author_id': [user, 'users'],
               'last_reply_id': [message, 'messages'],
           },
           o2m={
              'messages': [
                  message, 'parent_id'
              ],
              'attachments': [
                  attachment, 'container_id', 'container_type', 'Message',
              ],
              'watchers': [
                  watcher, 'watchable_id', 'watchable_type', 'Issue',
              ],
           },
    )[ENTITY]

def document_category(src):
    return fetch('enumerations', src,
           m2o={
              'parent_id': [issue_priority, 'enumerations'],
              'project_id': [project, 'projects']
           },
    )[ENTITY]

def news(src):
    return fetch('news', src,
           m2o={
               'project_id': [project, 'projects'],
               'author_id': [user, 'users'],
           },
           o2m={
              'attachments': [
                  attachment, 'container_id', 'container_type', 'News',
              ],
              'comments': [
                  comment, 'commented_id', 'commented_type', 'News',
              ],
              'watchers': [
                  watcher, 'watchable_id', 'watchable_type', 'News',
              ],
           },
    )[ENTITY]

def document(src):
    return fetch('documents', src,
           m2o={
               'project_id': [project, 'projects'],
               'category_id': [document_category, 'enumerations'],
           },
           o2m={
              'attachments': [
                  attachment, 'container_id', 'container_type', 'Document',
              ],
              'watchers': [
                  watcher, 'watchable_id', 'watchable_type', 'Document',
              ],
           },
    )[ENTITY]

def attachment(src):
    if not ssh: return
    callback = fetch('attachments', src,
           polymorphic={
               'container_id': ['container_type', {
                   'Issue': [issue, 'issues'],
                   'Document': [document, 'documents'],
                   'Message': [message, 'messages'],
                   'News': [news, 'news'],
                   'Project': [project, 'projects'],
                   'Version': [version, 'versions'],
                   'WikiPage': [wiki_page, 'wiki_pages'],
               }]
           },
           m2o={
               'author_id': [user, 'users']
           },
    )
    if not callback[AFFECTED]: return callback[ENTITY]
    print("downloading attachment #{0} from src".format(
        callback[ENTITY]['id']))
    sftp.get(config['dst']['path']+'/'+callback[ENTITY]['disk_filename'],
             config['src']['ssh']['path']+'/'+callback[ENTITY]['disk_filename'])
    return callback[ENTITY]

def comment(src):
    return fetch('comments', src,
           polymorphic={
               'commented_id': ['commented_type', {
                   'News': [news, 'news'],
               }]
           },
           m2o={
               'author_id': [user, 'users']
           },
    )[ENTITY]

def token(src):
    return fetch('tokens', src,
           m2o={
               'user_id': [user, 'users']
           },
    )[ENTITY]

def user_preference(src):
    return fetch('user_preferences', src,
           m2o={
               'user_id': [user, 'users']
           },
    )[ENTITY]

def watcher(src):
    return fetch('watchers', src,
           polymorphic={
               'watchable_id': ['watchable_type', {
                   'Board': [board, 'boards'],
                   'Issue': [issue, 'issues'],
                   'Message': [message, 'messages'],
                   'News': [news, 'news'],
                   'Wiki': [wiki, 'wikis'],
                   'WikiPage': [wiki_page, 'wiki_pages'],
               }]
           },
           m2o={
               'user_id': [user, 'users']
           },
    )[ENTITY]

def query(src):
    return fetch('queries', src,
           stub=['is_public'],
           translate={
               'visibility': (lambda src: 2 if src['is_public'] else 0)
           },
           m2o={
               'user_id': [user, 'users'],
               'project_id': [project, 'projects'],
           },
    )[ENTITY]

def workflow(src):
    return fetch('workflows', src,
           m2o={
               'tracker_id': [tracker, 'trackers'],
               'old_status_id': [issue_status, 'issue_statuses'],
               'new_status_id': [issue_status, 'issue_statuses'],
               'role_id': [role, 'roles'],
           },
    )[ENTITY]

def issue_relation(src):
    return fetch('issue_relations', src,
           m2o={
               'issue_from_id': [issue, 'issues'],
               'issue_to_id': [issue, 'issues'],
           },
    )[ENTITY]

def setting(src):
    return fetch('settings', src, pkey='name')[ENTITY]

def group(src):
    return fetch('users', src, stub=['reminder_notification'])[ENTITY]

def custom_field(src):
    return fetch('custom_fields', src)[ENTITY]

def custom_value(src):
    return fetch('custom_values', src,
           polymorphic={
               'customized_id': ['customized_type', {
                   'Project': [project, 'projects'],
                   'Issue': [issue, 'issues'],
               }]
           },
           m2o={
               'custom_field_id': [custom_field, 'custom_fields']
           },
    )[ENTITY]
