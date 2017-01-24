Redmine Individual Project Migration Tool
=========================================

Project Rescue
--------------

With that tool, you can migrate individual project from Redmine 2.x / 3.2
from an instance to another with all their dependencies (issues, users, parent
projects, children projects, news, documents, attachments, custom fields etc..)

It is a script made in Python3 so make sure that it is already installed.

You need to make sure to run that script into a fresh new installation
of Redmine, but you can use it many times after the first usage without
causing any problems. Simply : **You need to run the first migration in a
fresh new installation of Redmine**.

Al the IDs and primary keys will be kept original. The new IDs will be bumped
from the setting value `relative.new_sequence` described in 'Configuration
procedure' section of this document.

### License ###

This project is released under GNU GPLv3 license, don't hesitate to read
the `LICENSE` file for further informations.


### Installation procedure ###

You will need to install first `python3-pip` package
in order to run this command (that will install all dependencies) :

```bash
$ ./bootstrap
```

### Configuration procedure ###

Once you've installed the dependencies, you will need to copy the 
`config.yml.example` to `config.yml` and customize it accordingly to your needs:

```yaml
src:
    type: mysql
    name: redmine_official
    host: localhost
    user: root
    pass: test

dst:
    type: postgresql
    name: redmine_default
    host: 127.0.0.1
    user: postgres
    pass: test

relative:
    reference_table: issues
    new_sequence: 500000
```

The `relative.reference_table` is the table that will be used as a reference
point to set the key indexes, and new_sequence will be the minimum ID possible
for new primary keys in order to avoid collisions when you run the script
multiple times while using the Redmine target instance in production.

For example, if you have 150 000 issues and 345 000 time entries.

The new issues sequence will be set to 500 000, and the new time entries
sequence will be set to `(345 000 / 150 000) * 500 000 = 1 150 000`.


### Usage procedure ###

Once everything is installed and configured, you now can launch the migration.

```bash
$ ./migrate.py [PROJECT_SLUG_IDENTIFIER]
```

### Contributing to this tool ###

We absolutely appreciate patches, feel free to contribute
directly on the GitHub project.

Repositories / Development website / Bug Tracker:

https://github.com/dctremblay/Project-Rescue

Do not hesitate to join us and post comments, suggestions,
questions and general feedback directly on the issues tracker.

Author : David Côté-Tremblay <imdc.technologies@gmail.com>
