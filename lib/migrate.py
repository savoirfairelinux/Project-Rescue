from . import orm
from pprint import pprint

def init():
    print("initializing migration process")
    return orm.init()

def close(cn):
    print("closing connection with databases")
    orm.close(cn)

def bootstrap(project_identifier):
    project_obj = orm.findone(cn['src'], 'projects', {
        'identifier': project_identifier
    })
    if not project_obj:
        return False
    project(project_obj)
    orm.close(cn)
    return True

cn = init()

FUNC = 0
TABLE = 1
COLUMN = 1

def fetch(table, data, o2m={}, m2o={}, stub=[]):
    dst = orm.findone(cn['dst'], table, {'id': data['id']})
    if dst: return dst
    dst = dict(data)
    for s in stub:
        dst.pop(s, None)
    orm.insert(cn['dst'], table, dst)
    for column, scheme in m2o.items():
        if data[column]:
            scheme[FUNC](orm.findone(
                cn['src'], scheme[TABLE], {'id': dst[column]}
            ))
    for _table, scheme in o2m.items():
        for p in orm.find(cn['src'], _table, {scheme[COLUMN]: dst['id']}):
            scheme[FUNC](p)
    return dst

##################################################
def project(src):
    return fetch('projects', src, stub=['customer_id'],
           o2m={
               'projects': [project, 'parent_id'],
               'issues': [issue, 'project_id'],
               'enabled_modules': [enabled_module, 'project_id'],
               'time_entries': [time_entry, 'project_id'],
               'wikis': [wiki, 'project_id'],
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
           o2m={'issues': [issue, 'parent_id']},
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
    )

def tracker(src):
    return fetch('trackers', src)

def issue_category(src):
    return fetch('issue_categories', src,
           stub=['reminder_notification'],
           m2o={
              'assigned_to_id': [user, 'users'],
              'project_id': [project, 'projects']
           },
    )

def issue_status(src):
    return fetch('issue_statuses', src)

def user(src):
    return fetch('users', src, stub=['reminder_notification'])

def issue_priority(src):
    return fetch('enumerations', src,
           m2o={
              'parent_id': [issue_priority, 'enumerations'],
              'project_id': [project, 'projects']
           },
    )

def activity(src):
    return fetch('enumerations', src,
           m2o={
              'parent_id': [issue_priority, 'enumerations'],
              'project_id': [project, 'projects']
           },
    )

def version(src):
    return fetch('versions', src,
           stub=['sprint_start_date'],
           m2o={
              'project_id': [project, 'projects']
           },
    )

def enabled_module(src):
    return fetch('enabled_modules', src,
           m2o={
              'project_id': [project, 'projects']
           },
    )

def time_entry(src):
    return fetch('time_entries', src, stub=[],
           m2o={
               'project_id': [project, 'projects'],
               'user_id': [user, 'users'],
               'issue_id': [issue, 'issues'],
               'activity_id': [activity, 'enumerations'],
           },
    )

def wiki(src):
    return fetch('wikis', src,
           m2o={
              'project_id': [project, 'projects'],
           },
           o2m={'wiki_pages': [wiki_page, 'wiki_id'],
                'wiki_redirects': [wiki_redirect, 'wiki_id']},
    )

def wiki_page(src):
    return fetch('wiki_pages', src,
           m2o={
              'wiki_id': [wiki, 'wikis'],
              'parent_id': [wiki_page, 'wiki_pages'],
           },
           o2m={
              'wiki_pages': [wiki_page, 'parent_id'],
              'wiki_contents': [wiki_content, 'page_id'],
           },
    )

def wiki_content(src):
    return fetch('wiki_contents', src,
           m2o={
              'page_id': [wiki_page, 'wiki_pages'],
              'author_id': [user, 'users'],
           },
           o2m={
              'wiki_content_versions': [wiki_content_version, 'wiki_content_id'],
           },
    )

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
    )
