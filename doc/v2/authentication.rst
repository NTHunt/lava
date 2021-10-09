.. index:: user authentication

.. _user_authentication:

Configuring user authentication
===============================

The LAVA frontend is developed using the Django_ web application framework and
user authentication and authorization is based on the standard `Django auth
subsystems`_. This means that it is fairly easy to integrate authentication
against any source for which a Django backend exists. Discussed below are the
tested and supported authentication methods for LAVA.

.. _Django: https://www.djangoproject.com/
.. _`Django auth subsystems`: https://docs.djangoproject.com/en/dev/topics/auth/

.. note:: LAVA used to include support for OpenID authentication (prior to
   version 2016.8), but this support had to be **removed** when incompatible
   changes in Django (version 1.8) caused it to break.

Local Django user accounts are supported. When using local Django user
accounts, new user accounts need to be created by Django admin prior to use.

.. seealso:: :ref:`admin_adding_users`

.. _ldap_authentication:

Using Lightweight Directory Access Protocol (LDAP)
--------------------------------------------------

LAVA server may be configured to authenticate via Lightweight
Directory Access Protocol (LDAP). LAVA uses the `django_auth_ldap`_
backend for LDAP authentication.

.. _`django_auth_ldap`: https://django-auth-ldap.readthedocs.io/en/latest/

LDAP server support is configured using the following parameters in
``/etc/lava-server/settings.conf`` (JSON syntax)::

  "AUTH_LDAP_SERVER_URI": "ldap://ldap.example.com",
  "AUTH_LDAP_BIND_DN": "",
  "AUTH_LDAP_BIND_PASSWORD": "",
  "AUTH_LDAP_USER_DN_TEMPLATE": "uid=%(user)s,ou=users,dc=example,dc=com",
  "AUTH_LDAP_USER_ATTR_MAP": {
    "first_name": "givenName",
    "email": "mail"
  },

Use the following parameter to configure a custom LDAP login page
message::

    "LOGIN_MESSAGE_LDAP": "If your Linaro email is first.second@linaro.org then use first.second as your username"

Other supported parameters are::

  "AUTH_LDAP_GROUP_SEARCH": "LDAPSearch('ou=groups,dc=example,dc=com', ldap.SCOPE_SUBTREE, '(objectClass=groupOfNames)'",
  "AUTH_LDAP_USER_FLAGS_BY_GROUP": {
    "is_active": "cn=active,ou=django,ou=groups,dc=example,dc=com",
    "is_staff": "cn=staff,ou=django,ou=groups,dc=example,dc=com",
    "is_superuser": "cn=superuser,ou=django,ou=groups,dc=example,dc=com"
  }

Similarly::

  "AUTH_LDAP_USER_SEARCH": "LDAPSearch('o=base', ldap.SCOPE_SUBTREE, '(uid=%(user)s)')"

.. note:: If you need to make deeper changes that don't fit into the
          exposed configuration, it is quite simple to tweak things in
          the code here. Edit
          ``/usr/lib/python3/dist-packages/lava_server/settings/common.py``

Restart the ``lava-server`` and ``apache2`` services after any
changes.

Using GitLab
------------

LAVA server can delegate its authentication to a GitLab installation
using the `django_allauth`_ authentication backend.

.. _`django_allauth`: https://django-allauth.readthedocs.io/en/latest/

To enable GitLab authentication support you need to set `AUTH_GITLAB_URL`
in your LAVA configuration. Do this by placing a config snippet in yaml format
in the directory ``/etc/lava-server/settings.d``::

  AUTH_GITLAB_URL: "https://gitlab.example.com"

This requires django-allauth to be installed manually (e.g., on Debian
you would install the package ``python3-django-allauth``). Afterwards,
run ``lava-server manage migrate``.

Restart the ``lava-server`` and ``apache2`` services after any changes.

Before you can use `GitLab OAuth2 authentication`_, some additional setup steps
need to be performed:

.. _`GitLab OAuth2 authentication`: https://docs.gitlab.com/ce/integration/oauth_provider.html

* In your GitLab instance, you need to add your LAVA installation as an
  **Application**, and enable the ``read_user`` scope.

* The Redirect URI is the URL where users are sent after they authorize with
  GitLab. The form is: `LAVA_URL/accounts/gitlab/login/callback/`
  Currently there seems to be a bug in GitLab so the Redirect URI works only
  with **http** protocol.

* After saving the application in GitLab, you will be provided with an
  **Application ID** and a **Secret**.

* In your LAVA administration dashboard, go to **Social Accounts** and
  add a **Social application**. Select **GitLab** as provider and
  enter the credentials you obtained from GitLab as **Client id** and
  **Secret key**.

* While adding the **Social application** make sure to move the sites
  you will use GitLab to authenticate from the **Available sites** to
  **Chosen sites** on the **Sites** tables or ``allauth`` will raise
  an exception saying a matching query does not exist.

.. note:: If SMTP is not set up in LAVA, you can get a 500 Internal server
          error. Login will still work despite the error.

Using GitHub
------------

LAVA server can also use GitHub as its authentication server.
To enable it, you need to set 'AUTH_GITHUB_ENABLE: True'
in your LAVA configuration. Do this by placing a config snippet in yaml format
in the directory ``/etc/lava-server/settings.d``.
It also requires django-allauth to be installed if it hasn't been done.
Follow the instructions in the Using GitLab session above to install the module.

Before you can use `GitHub Authentication`_, some additional setup steps need to
be performed:

.. _`GitHub Authentication`: https://docs.github.com/en/developers/apps/building-oauth-apps/authorizing-oauth-apps

* Navigate to `https://github.com/settings/applications/new` and create a new
  OAuth application

* The Homepage URL is your LAVA server URL

* The Authorization callback URL is the URL where users are sent after they authorize
  with GitHub. The form is: `LAVA_URL/accounts/github/login/callback/`

* Generate a new client secret

* In your LAVA administration dashboard, go to **Social Accounts** and
  add a **Social application**. Select **GitHub** as provider and
  enter the credentials you obtained from GitHub as **Client ID** and
  the **Client secret** you just generated

* Move the sites that you will use GitHub to authenticate from the 
  **Available sites** to **Chosen site** on the **Sites** tables.
