# RSS Feed

```bash
AWS_FEED='https://aws.amazon.com/new/feed/'
BURP_VERSION_FEED='https://portswigger.net/burp/releases/rss'
GITLAB_VERSION_FEED='https://about.gitlab.com/all-releases.xml'

OPENSSL_FEED='https://github.com/openssl/openssl/releases.atom'
KUBECTL_FEED='https://github.com/kubernetes/kubernetes/releases.atom'
IAM_AUTHENTICATOR_FEED='https://github.com/kubernetes-sigs/aws-iam-authenticator/releases.atom'
HELM_FEED='https://github.com/helm/helm/releases.atom'

AWS_CLI_FEED='https://github.com/aws/aws-cli/tags.atom'
CORRETO_11_FEED='https://github.com/corretto/corretto-11/releases.atom'
CORRETO_17_FEED='https://github.com/corretto/corretto-17/releases.atom'
MAVEN_FEED='https://github.com/apache/maven/releases.atom'
NODEJS_FEED='https://github.com/nodejs/node/releases.atom'
SONARQUBE_FEED='https://github.com/SonarSource/sonar-scanner-cli/releases.atom'
SONAR_SCANNER_CLI_FEED='https://github.com/SonarSource/sonarqube/releases.atom'
DEPENDENCY_CHECK_FEED='https://github.com/jeremylong/DependencyCheck/releases.atom'
```

# Bot

File structure

```bash
aws_lambda
 ├── lambda_function.py // Main class
 ├── classes.py // Helper classes
 ├── cached.txt // Cached values
 ├── package // pip install dependencies here
 └── python-package.zip // to upload to lambda - Run shell script provided below to generate this zip file
```

Dependencies

```bash
pip install --target ./package requests feedparser python-dateutil telebot
```

Cached.txt

```bash
GITLAB,https://about.gitlab.com/releases/2023/03/02/security-release-gitlab-15-9-2-released/
```

Shell (Run this script to package zip file for lambda file upload)

```python
#!/bin/bash

FILE=python-package.zip
if [ -f "$FILE" ]; then
    echo "$FILE exists."
		rm -r "$FILE"
fi

cd package
zip -r ../python-package.zip .
cd ..
zip python-package.zip lambda_function.py classes.py cached.txt
```

## Important Notes

### Constraints with Github’s release atom

`release.atom` includes pre-releases. There is no way to differentiate pre-releases from stable releases in RSS.

The only way would be github API

[Releases - GitHub Docs](https://docs.github.com/en/rest/releases/releases?apiVersion=2022-11-28#get-a-release-by-tag-name)

```bash
curl \
  -H "Accept: application/vnd.github+json" \
  -H "Authorization: Bearer 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"\
  -H "X-GitHub-Api-Version: 2022-11-28" \
  https://api.github.com/repos/kubernetes/kubernetes/releases/tags/v1.27.0-alpha.2 | jq '.prerelease'
```

response

```bash
true
```

### Considerations with filtering pre-releases out from RSS feed

**TODO**: test releasing pre-release → release tag

**Potential Issue**: if github considers an entry (regardless of its release type tag) as the same entity object, the ‘published’ timestamp will not be updated even if the team updates a pre-release to an official release. The only property change would be the release type. 

This poses an issue as atp when it is still a pre-release item, it has already been filtered out from RSS feed for new updates. When the time comes where the item is updated to an official release, given that its published date remains the same as before, it is no longer considered as a new update.

+ additionally, for code enhancement to exit search loop upon older entry (assuming order of entries in RSS feed are by timestamp desc). Even if published date is updated. as long as the order of the entry in the list remains the same, it might still be filtered out since the early exit loop condition is met.

**Conclusion**:

Best to include pre-releases in feed to rss bot and do due diligence to check manually

### Workaround

Add command to Helper Bot to retrieve the latest official release with github api call.

## Planning

In general, the output variables from RSS feed are the same:

```python
'title': 'string'
'published': 'GMT/UTC time format', 
'summary': "string", 
'link': 'string'
```

Filter recent feed by `published` value

```python
if datetime.now() - published <= 24 hours:
		send_message(...)
```

- Frequency: Once daily *or wtv that’s preferred*
- Challenge to schedule more than once daily as Gitlab RSS feed does not provide timestamp, only the date → will send duplicates unless memorization/cached
    - Eg: Scheduled job at 10am daily, gitlab releases new update at 5pm (published value will be *2023-02-14T00:00:00+00:00*). This entry will be filtered out as it’s treated > 24 hours.

### Deviations

Adding onto filtering published value, other factors should be accounted for.

1. Burpsuite
    - Show enterprise edition releases only
        
        Filter by title 
        
        ```python
        'title': 'Enterprise Edition 2023.1',
        ```
        
        ```python
        def send_burp_release(entry):
            BURP_KEYWORD = 'enterprise'
            is_enterprise = BURP_KEYWORD in entry.title.lower()
            if is_enterprise:
                send_message(...)
        ```
        
    - `Published` timestamp in GMT
2. Gitlab
    
    Inaccuracies in filtering entries by published due to the lack of timestamp - all set to 00:00. Alternative filtering method would be store the latest entry’s link and filter entries that comes after it
    
    - Cache/Store the latest entry’s link
        
        ```python
        'link': 'https://about.gitlab.com/releases/2023/02/14/gitlab-15-8-3-released/', 
        ```
        
        ```python
        cached_latest = ...
        latest = ...
        encounteredLatest = false
        for entry in rss_feed.entries:
        		if entry.link == cached_latest:
        				break # exit loop
        		else if !encounteredLatest:
        				latest = entry.link
        				send_message(...)
        		else:
        				send_message(...)
        # update cache if encountered latest feed
        if encounteredLatest:
        		cached_latest = latest
        ```
        
3. OpenSSL
    - Shows openssl 1.x.x releases only
        
        Use regex pattern matching on `link`
        
        ```python
        'link': 'https://github.com/openssl/openssl/releases/tag/openssl-3.0.8'
        ```
        
        ```python
        import re
        
        for entry in rss_feed.entries:
        	tag = entry.link.split('/')[-1]
        	regex = "^openssl_1_*"
        	pattern = re.compile(regex)
        	if pattern.match(tag.lower()):
        		send_message(...)
        ```
        
4. NodeJs
    - Shows nodejs 14.x and 18.x releases only
        
        Use regex pattern matching on `link`
        
        ```python
        'link': 'https://github.com/nodejs/node/releases/tag/v19.7.0'
        ```
        
        ```python
        import re
        
        for entry in rss_feed.entries:
        	tag = entry.link.split('/')[-1]
        	nodejs_14_pattern = re.compile("^v14.*")
        	nodejs_18_pattern = re.compile("^v18.*")
        	if nodejs_14_pattern.match(tag.lower()) or nodejs_18_pattern.match(tag.lower()):
        		send_message(...)
        ```
        
5. AWS Cli
    - Shows v2.x releases only
        
        Use regex pattern matching on `link`
        
        ```bash
        https://github.com/aws/aws-cli/releases/tag/2.11.2
        ```
        
        ```bash
        str = entry.link.split('/')[-1].lower()
        v2_pattern = re.compile("^2.*")
        if v2_pattern.match(str.lower()):
           return True
        return False
        ```
        
6. Sonarqube
    - Shows version 8.x releases only
        
        Use regex pattern matching on `link`
        
        ```python
        'link': 'https://github.com/SonarSource/sonarqube/releases/tag/9.9.0.65466'
        ```
        
        ```python
        import re
        
        for entry in rss_feed.entries:
        	tag = entry.link.split('/')[-1]
        	npattern = re.compile("^8.*")
        	if pattern.match(tag.lower()):
        		send_message(...)
        ```
        

## # DSO Tools

## Burpsuite Feed

URL

```bash
https://portswigger.net/burp/releases/rss
```

Key components

```bash
'title': 'Enterprise Edition 2023.1',
'published': 'Mon, 23 Jan 2023 15:20:45 GMT', 
'summary': "This release introduces support for popup windows when recording logins. We've also added checks that enable you to make sure your infrastructure meets the minimum system requirements. In addition, th", 
'link': 'https://portswigger.net/burp/releases/enterprise-edition-2023-1'
```

raw sample rss entry

```bash
{
'id': 'enterprise-edition-2023-1', 
'guidislink': False, 
'published': 'Mon, 23 Jan 2023 15:20:45 GMT', 
'published_parsed': 
		time.struct_time(
				tm_year=2023, 
				tm_mon=1, 
				tm_mday=23, 
				tm_hour=15, 
				tm_min=20, 
				tm_sec=45, 
				tm_wday=0, 
				tm_yday=23, 
				tm_isdst=0), 
'title': 'Enterprise Edition 2023.1', 
'title_detail': 
	{'type': 'text/plain', 
		'language': None, 
		'base': 'https://portswigger.net/burp/releases/rss', 
		'value': 'Enterprise Edition 2023.1'
	}, 
'summary': "This release introduces support for popup windows when recording logins. We've also added checks that enable you to make sure your infrastructure meets the minimum system requirements. In addition, th", 
'summary_detail': 
	{'type': 'text/html', 
		'language': None, 
		'base': 'https://portswigger.net/burp/releases/rss', 
		'value': "This release introduces support for popup windows when recording logins. We've also added checks that enable you to make sure your infrastructure meets the minimum system requirements. In addition, th"
	}, 
'links': [
	{'rel': 'alternate', 'type': 'text/html', 'href': 'https://portswigger.net/burp/releases/enterprise-edition-2023-1'}
], 
'link': 'https://portswigger.net/burp/releases/enterprise-edition-2023-1', 
'media_thumbnail': [{'url': 'https://portswigger.net'}], 
'href': ''
}
```

## Gitlab Feed

URL

```bash
https://about.gitlab.com/all-releases.xml
```

Key components

- *Note: no timestamp on published - only date is available*

```bash
'title': 'GitLab Patch Release: 15.8.3',
'published': '2023-02-14T00:00:00+00:00',
'summary': '<!-- For detailed instructions on how to complete this, please see https://gitlab.com/gitlab-org/release/docs/blob/master/general/patch/blog-post.md -->\n\n<p>Today we are releasing version 15.8.3 for GitLab Community Edition and Enterprise Edition.</p>\n\n<p>This version resolves a number of regressions and bugs in\n<a href="https://about.gitlab.com/releases/2023/01/22/gitlab-15-8-released/">this month\'s 15.8 release</a> and\nprior versions.</p>\n\n<h2 id="gitlab-community-edition-and-enterprise-edition">GitLab Community Edition and Enterprise Edition</h2>\n\n<!--\n- [Description](GitLab MR LINK)\n- [Description](GitLab MR LINK)\n-->\n\n<ul>\n  <li><a href="https://gitlab.com/gitlab-org/gitlab/-/merge_requests/108838">Deprecate backup upload using Openstack Swift and Rackspace APIs</a></li>\n  <li><a href="https://gitlab.com/gitlab-org/gitlab/-/merge_requests/108849">Note about Openstack and Rackspace API removal</a></li>\n  <li><a href="https://gitlab.com/gitlab-org/gitlab/-/merge_requests/109161">Updating nav and top level</a></li>\n  <li><a href="https://gitlab.com/gitlab-org/gitlab/-/merge_requests/109297">Update feature flag status of GitHub gists feature</a></li>\n  <li><a href="https://gitlab.com/gitlab-org/gitlab/-/merge_requests/109386">What\'s New post for 15.8</a></li>\n  <li><a href="https://gitlab.com/gitlab-org/gitlab/-/merge_requests/109636">Add version note to email feature</a></li>\n  <li><a href="https://gitlab.com/gitlab-org/gitlab/-/merge_requests/109882">Revert changes on wiki replication/verification legacy code</a></li>\n  <li><a href="https://gitlab.com/gitlab-org/gitlab/-/merge_requests/109945">Handle client disconnects better in workhorse</a></li>\n  <li><a href="https://gitlab.com/gitlab-org/gitlab/-/merge_requests/110886">Attempt reading schema file instead of a file named <code>#{report_version}</code></a></li>\n  <li><a href="https://gitlab.com/gitlab-org/gitlab/-/merge_requests/110934">Upgrade Alert - Add proper API support</a>\n<!-- {{ MERGE_REQUEST_LIST }} --></li>\n</ul>\n\n<h2 id="important-notes-on-upgrading">Important notes on upgrading</h2>\n\n<p>This version does not include any new migrations, and for multi-node deployments, <a href="https://docs.gitlab.com/ee/update/#upgrading-without-downtime">should not require any downtime</a>.</p>\n\n<p>Please be aware that by default the Omnibus packages will stop, run migrations,\nand start again, no matter how “big” or “small” the upgrade is. This behavior\ncan be changed by adding a <a href="http://docs.gitlab.com/omnibus/update/README.html"><code>/etc/gitlab/skip-auto-reconfigure</code></a> file,\nwhich is only used for <a href="https://docs.gitlab.com/omnibus/update/README.html">updates</a>.</p>\n\n<h2 id="updating">Updating</h2>\n\n<p>To update, check out our <a href="https://about.gitlab.com/update/">update page</a>.</p>\n\n<h2 id="gitlab-subscriptions">GitLab subscriptions</h2>\n\n<p>Access to GitLab Premium and Ultimate features is granted by a paid <a href="https://about.gitlab.com/pricing/">subscription</a>.</p>\n\n<p>Alternatively, <a href="https://gitlab.com/users/sign_in">sign up for GitLab.com</a>\nto use GitLab\'s own infrastructure.</p>\n<img class="webfeedsFeaturedVisual" src="https://about.gitlab.com/images/default-blog-image.png" style="display: none;" />'
'link': 'https://about.gitlab.com/releases/2023/02/14/gitlab-15-8-3-released/', 
```

raw sample rss entry

```bash
{
'title': 'GitLab Patch Release: 15.8.3', 
'title_detail': 
	{'type': 'text/plain', 
		'language': None, 
		'base': 'https://about.gitlab.com/all-releases.xml', 
		'value': 'GitLab Patch Release: 15.8.3'
	}, 
'release': '', 
'links': [
	{'href': 'https://about.gitlab.com/releases/2023/02/14/gitlab-15-8-3-released/', 
		'rel': 'alternate', 'type': 'text/html'}
], 
'link': 'https://about.gitlab.com/releases/2023/02/14/gitlab-15-8-3-released/', 
'id': 'https://about.gitlab.com/releases/2023/02/14/gitlab-15-8-3-released/', '
guidislink': False, 
'published': '2023-02-14T00:00:00+00:00', 
'published_parsed': 
		time.struct_time(
				tm_year=2023, 
				tm_mon=2, 
				tm_mday=14, 
				tm_hour=0, 
				tm_min=0, 
				tm_sec=0, 
				tm_wday=1, 
				tm_yday=45, 
				tm_isdst=0), 
'updated': '2023-02-14T00:00:00+00:00', 
'updated_parsed': 
		time.struct_time(
				tm_year=2023, 
				tm_mon=2, 
				tm_mday=14, 
				tm_hour=0, 
				tm_min=0, 
				tm_sec=0, 
				tm_wday=1, 
				tm_yday=45, 
				tm_isdst=0), 
'authors': [{'name': 'Reuben Pereira'}], 
'author_detail': {'name': 'Reuben Pereira'}, 
'author': 'Reuben Pereira', 
'content': [
	{'type': 'text/html', 
		'language': None, 
		'base': 'https://about.gitlab.com/all-releases.xml', 
		'value': '<!-- For detailed instructions on how to complete this, please see https://gitlab.com/gitlab-org/release/docs/blob/master/general/patch/blog-post.md -->\n\n<p>Today we are releasing version 15.8.3 for GitLab Community Edition and Enterprise Edition.</p>\n\n<p>This version resolves a number of regressions and bugs in\n<a href="https://about.gitlab.com/releases/2023/01/22/gitlab-15-8-released/">this month\'s 15.8 release</a> and\nprior versions.</p>\n\n<h2 id="gitlab-community-edition-and-enterprise-edition">GitLab Community Edition and Enterprise Edition</h2>\n\n<!--\n- [Description](GitLab MR LINK)\n- [Description](GitLab MR LINK)\n-->\n\n<ul>\n  <li><a href="https://gitlab.com/gitlab-org/gitlab/-/merge_requests/108838">Deprecate backup upload using Openstack Swift and Rackspace APIs</a></li>\n  <li><a href="https://gitlab.com/gitlab-org/gitlab/-/merge_requests/108849">Note about Openstack and Rackspace API removal</a></li>\n  <li><a href="https://gitlab.com/gitlab-org/gitlab/-/merge_requests/109161">Updating nav and top level</a></li>\n  <li><a href="https://gitlab.com/gitlab-org/gitlab/-/merge_requests/109297">Update feature flag status of GitHub gists feature</a></li>\n  <li><a href="https://gitlab.com/gitlab-org/gitlab/-/merge_requests/109386">What\'s New post for 15.8</a></li>\n  <li><a href="https://gitlab.com/gitlab-org/gitlab/-/merge_requests/109636">Add version note to email feature</a></li>\n  <li><a href="https://gitlab.com/gitlab-org/gitlab/-/merge_requests/109882">Revert changes on wiki replication/verification legacy code</a></li>\n  <li><a href="https://gitlab.com/gitlab-org/gitlab/-/merge_requests/109945">Handle client disconnects better in workhorse</a></li>\n  <li><a href="https://gitlab.com/gitlab-org/gitlab/-/merge_requests/110886">Attempt reading schema file instead of a file named <code>#{report_version}</code></a></li>\n  <li><a href="https://gitlab.com/gitlab-org/gitlab/-/merge_requests/110934">Upgrade Alert - Add proper API support</a>\n<!-- {{ MERGE_REQUEST_LIST }} --></li>\n</ul>\n\n<h2 id="important-notes-on-upgrading">Important notes on upgrading</h2>\n\n<p>This version does not include any new migrations, and for multi-node deployments, <a href="https://docs.gitlab.com/ee/update/#upgrading-without-downtime">should not require any downtime</a>.</p>\n\n<p>Please be aware that by default the Omnibus packages will stop, run migrations,\nand start again, no matter how “big” or “small” the upgrade is. This behavior\ncan be changed by adding a <a href="http://docs.gitlab.com/omnibus/update/README.html"><code>/etc/gitlab/skip-auto-reconfigure</code></a> file,\nwhich is only used for <a href="https://docs.gitlab.com/omnibus/update/README.html">updates</a>.</p>\n\n<h2 id="updating">Updating</h2>\n\n<p>To update, check out our <a href="https://about.gitlab.com/update/">update page</a>.</p>\n\n<h2 id="gitlab-subscriptions">GitLab subscriptions</h2>\n\n<p>Access to GitLab Premium and Ultimate features is granted by a paid <a href="https://about.gitlab.com/pricing/">subscription</a>.</p>\n\n<p>Alternatively, <a href="https://gitlab.com/users/sign_in">sign up for GitLab.com</a>\nto use GitLab\'s own infrastructure.</p>\n<img class="webfeedsFeaturedVisual" src="https://about.gitlab.com/images/default-blog-image.png" style="display: none;" />'}
], 
'summary': '<!-- For detailed instructions on how to complete this, please see https://gitlab.com/gitlab-org/release/docs/blob/master/general/patch/blog-post.md -->\n\n<p>Today we are releasing version 15.8.3 for GitLab Community Edition and Enterprise Edition.</p>\n\n<p>This version resolves a number of regressions and bugs in\n<a href="https://about.gitlab.com/releases/2023/01/22/gitlab-15-8-released/">this month\'s 15.8 release</a> and\nprior versions.</p>\n\n<h2 id="gitlab-community-edition-and-enterprise-edition">GitLab Community Edition and Enterprise Edition</h2>\n\n<!--\n- [Description](GitLab MR LINK)\n- [Description](GitLab MR LINK)\n-->\n\n<ul>\n  <li><a href="https://gitlab.com/gitlab-org/gitlab/-/merge_requests/108838">Deprecate backup upload using Openstack Swift and Rackspace APIs</a></li>\n  <li><a href="https://gitlab.com/gitlab-org/gitlab/-/merge_requests/108849">Note about Openstack and Rackspace API removal</a></li>\n  <li><a href="https://gitlab.com/gitlab-org/gitlab/-/merge_requests/109161">Updating nav and top level</a></li>\n  <li><a href="https://gitlab.com/gitlab-org/gitlab/-/merge_requests/109297">Update feature flag status of GitHub gists feature</a></li>\n  <li><a href="https://gitlab.com/gitlab-org/gitlab/-/merge_requests/109386">What\'s New post for 15.8</a></li>\n  <li><a href="https://gitlab.com/gitlab-org/gitlab/-/merge_requests/109636">Add version note to email feature</a></li>\n  <li><a href="https://gitlab.com/gitlab-org/gitlab/-/merge_requests/109882">Revert changes on wiki replication/verification legacy code</a></li>\n  <li><a href="https://gitlab.com/gitlab-org/gitlab/-/merge_requests/109945">Handle client disconnects better in workhorse</a></li>\n  <li><a href="https://gitlab.com/gitlab-org/gitlab/-/merge_requests/110886">Attempt reading schema file instead of a file named <code>#{report_version}</code></a></li>\n  <li><a href="https://gitlab.com/gitlab-org/gitlab/-/merge_requests/110934">Upgrade Alert - Add proper API support</a>\n<!-- {{ MERGE_REQUEST_LIST }} --></li>\n</ul>\n\n<h2 id="important-notes-on-upgrading">Important notes on upgrading</h2>\n\n<p>This version does not include any new migrations, and for multi-node deployments, <a href="https://docs.gitlab.com/ee/update/#upgrading-without-downtime">should not require any downtime</a>.</p>\n\n<p>Please be aware that by default the Omnibus packages will stop, run migrations,\nand start again, no matter how “big” or “small” the upgrade is. This behavior\ncan be changed by adding a <a href="http://docs.gitlab.com/omnibus/update/README.html"><code>/etc/gitlab/skip-auto-reconfigure</code></a> file,\nwhich is only used for <a href="https://docs.gitlab.com/omnibus/update/README.html">updates</a>.</p>\n\n<h2 id="updating">Updating</h2>\n\n<p>To update, check out our <a href="https://about.gitlab.com/update/">update page</a>.</p>\n\n<h2 id="gitlab-subscriptions">GitLab subscriptions</h2>\n\n<p>Access to GitLab Premium and Ultimate features is granted by a paid <a href="https://about.gitlab.com/pricing/">subscription</a>.</p>\n\n<p>Alternatively, <a href="https://gitlab.com/users/sign_in">sign up for GitLab.com</a>\nto use GitLab\'s own infrastructure.</p>\n<img class="webfeedsFeaturedVisual" src="https://about.gitlab.com/images/default-blog-image.png" style="display: none;" />'
}
```

## # Management Client Tools

## OpenSSL Feed

URL

```bash
https://github.com/openssl/openssl/releases.atom
```

Key components

```bash
'title': 'OpenSSL 3.0.8', 
'updated': '2023-02-08T08:31:14Z',
'summary': '<p>OpenSSL 3.0.8 is now available, including bug and security fixes</p>', 
'link': 'https://github.com/openssl/openssl/releases/tag/openssl-3.0.8'
```

Filters

- To filter and show updates of openssl 1.x.x only
- Use link as input to filter. Use / slash to get last component (eg. `openssl_1_1_1s` of `https://github.com/openssl/openssl/releases/tag/OpenSSL_1_1_1s`)
- Delimiter for pattern matching set as _ underscore (eg. `OpenSSL_1_1_1t`vs `openssl-3.0.8`)
- Search pattern should be case-insensitive (inconsistent naming in lower/upper cases)

Constraint

- Cannot filter pre-releases as there is no identifier within entry to distinguish release types
    - Requires Gitlab API

raw sample rss entry

```bash
{
'id': 'tag:github.com,2008:Repository/7634677/openssl-3.0.8', 
'guidislink': True, 
'link': 'https://github.com/openssl/openssl/releases/tag/openssl-3.0.8', 
'updated': '2023-02-08T08:31:14Z', 
'updated_parsed': 
		time.struct_time(
				tm_year=2023, 
				tm_mon=2, 
				tm_mday=8, 
				tm_hour=8, 
				tm_min=31, 
				tm_sec=14, 
				tm_wday=2, 
				tm_yday=39, 
				tm_isdst=0), 
'links': [
		{'rel': 'alternate', 'type': 'text/html', 
		'href': 'https://github.com/openssl/openssl/releases/tag/openssl-3.0.8'}], 
'title': 'OpenSSL 3.0.8', 
'title_detail': 
		{'type': 'text/plain', 
			'language': 'en-US', 
			'base': 'https://github.com/openssl/openssl/releases.atom', 
			'value': 'OpenSSL 3.0.8'
		}, 
'content': [
		{'type': 'text/html', 
			'language': 'en-US', 
			'base': 'https://github.com/openssl/openssl/releases.atom', 
			'value': '<p>OpenSSL 3.0.8 is now available, including bug and security fixes</p>'}
], 
'summary': '<p>OpenSSL 3.0.8 is now available, including bug and security fixes</p>', 
'authors': [{'name': 't8m'}], 
'author_detail': {'name': 't8m'}, 
'author': 't8m', 
'media_thumbnail': [
	{'height': '30', 'width': '30', 'url': 'https://avatars.githubusercontent.com/u/7125407?s=60&v=4'}
], 
'href': ''
}
```

## KubeCTL Feed

URL

```bash
https://github.com/kubernetes/kubernetes/releases.atom
```

Key components

```bash
'title': 'Kubernetes v1.27.0-alpha.2', 
'updated': '2023-02-15T04:19:45Z',
'summary': '<p>See <a href="https://groups.google.com/forum/#!forum/kubernetes-announce" rel="nofollow">kubernetes-announce@</a>. Additional binary downloads are linked in the <a href="https://github.com/kubernetes/kubernetes/blob/master/CHANGELOG/CHANGELOG-1.27.md">CHANGELOG</a>.</p>\n<p>See <a href="https://github.com/kubernetes/kubernetes/blob/master/CHANGELOG/CHANGELOG-1.27.md">the CHANGELOG</a> for more details.</p>', 
'link': 'https://github.com/kubernetes/kubernetes/releases/tag/v1.27.0-alpha.2',
```

Constraint

- Cannot filter pre-releases as there is no identifier within entry to distinguish release types
    - Requires Gitlab API

raw sample rss entry

```bash
{
'id': 'tag:github.com,2008:Repository/20580498/v1.27.0-alpha.2', 
'guidislink': True, 
'link': 'https://github.com/kubernetes/kubernetes/releases/tag/v1.27.0-alpha.2', 
'updated': '2023-02-15T04:19:45Z', 
'updated_parsed': 
		time.struct_time(
				tm_year=2023, 
				tm_mon=2, 
				tm_mday=15, 
				tm_hour=4, 
				tm_min=19, 
				tm_sec=45, 
				tm_wday=2, 
				tm_yday=46, 
				tm_isdst=0), 
'links': [
	{'rel': 'alternate', 'type': 'text/html', 
		'href': 'https://github.com/kubernetes/kubernetes/releases/tag/v1.27.0-alpha.2'}
], 
'title': 'Kubernetes v1.27.0-alpha.2', 
'title_detail': 
		{'type': 'text/plain', 
		'language': 'en-US', 
		'base': 'https://github.com/kubernetes/kubernetes/releases.atom', 
		'value': 'Kubernetes v1.27.0-alpha.2'}, 
'content': [
	{'type': 'text/html', 
		'language': 'en-US', 
		'base': 'https://github.com/kubernetes/kubernetes/releases.atom', 
		'value': '<p>See <a href="https://groups.google.com/forum/#!forum/kubernetes-announce" rel="nofollow">kubernetes-announce@</a>. Additional binary downloads are linked in the <a href="https://github.com/kubernetes/kubernetes/blob/master/CHANGELOG/CHANGELOG-1.27.md">CHANGELOG</a>.</p>\n<p>See <a href="https://github.com/kubernetes/kubernetes/blob/master/CHANGELOG/CHANGELOG-1.27.md">the CHANGELOG</a> for more details.</p>'}
], 
'summary': '<p>See <a href="https://groups.google.com/forum/#!forum/kubernetes-announce" rel="nofollow">kubernetes-announce@</a>. Additional binary downloads are linked in the <a href="https://github.com/kubernetes/kubernetes/blob/master/CHANGELOG/CHANGELOG-1.27.md">CHANGELOG</a>.</p>\n<p>See <a href="https://github.com/kubernetes/kubernetes/blob/master/CHANGELOG/CHANGELOG-1.27.md">the CHANGELOG</a> for more details.</p>', 
'authors': [{'name': 'k8s-release-robot'}], 
'author_detail': {'name': 'k8s-release-robot'}, 
'author': 'k8s-release-robot', 
'media_thumbnail': [
	{'height': '30', 'width': '30', 'url': 'https://avatars.githubusercontent.com/u/33505452?s=60&v=4'}
], 
'href': ''
}
```

## IAM Authenticator Feed

URL

```bash
https://github.com/kubernetes-sigs/aws-iam-authenticator/releases.atom
```

Key components

```bash
'title': 'v0.6.4'
'updated': '2023-02-21T00:16:05Z', 

'link': 'https://github.com/kubernetes-sigs/aws-iam-authenticator/releases/tag/v0.6.4',
```

Constraint

- Summary param does not provide information about the version update
- Cannot filter pre-releases as there is no identifier within entry to distinguish release types
    - Requires Gitlab API
    

raw sample rss entry

```bash
{
'id': 'tag:github.com,2008:Repository/99036030/v0.6.4', 
'guidislink': True, 
'link': 'https://github.com/kubernetes-sigs/aws-iam-authenticator/releases/tag/v0.6.4', 
'updated': '2023-02-21T00:16:05Z', 
'updated_parsed': 
		time.struct_time(
				tm_year=2023, 
				tm_mon=2, 
				tm_mday=21, 
				tm_hour=0, 
				tm_min=16, 
				tm_sec=5, 
				tm_wday=1, 
				tm_yday=52, 
				tm_isdst=0), 
'links': [
	{'rel': 'alternate', 'type': 'text/html', 
		'href': 'https://github.com/kubernetes-sigs/aws-iam-authenticator/releases/tag/v0.6.4'}
], 
'title': 'v0.6.4', 
'title_detail': 
	{'type': 'text/plain', 
		'language': 'en-US', 
		'base': 'https://github.com/kubernetes-sigs/aws-iam-authenticator/releases.atom', 
		'value': 'v0.6.4'}, 
'content': [
	{'type': 'text/html', 
		'language': 'en-US', 
		'base': 'https://github.com/kubernetes-sigs/aws-iam-authenticator/releases.atom', 
		'value': '<p>Release 0.6.4</p>'}
], 
'summary': '<p>Release 0.6.4</p>', 
'authors': [{'name': 'actions-user'}], 
'author_detail': {'name': 'actions-user'}, 
'author': 'actions-user', 
'media_thumbnail': [
	{'height': '30', 'width': '30', 'url': 'https://avatars.githubusercontent.com/u/65916846?s=60&v=4'}
], 
'href': ''
}
```

## Helm Feed

URL

```bash
https://github.com/helm/helm/releases.atom
```

Key components

```bash
'title': 'Helm v3.11.1',
'updated': '2023-02-16T20:36:58Z',
'summary': '<p>Helm v3.11.1 is a security (patch) release. Users are strongly recommended to update to this release.</p>\n<p>The template function <code>getHostByName</code> can be used to disclose information. More details are available in the <a href="https://github.com/helm/helm/security/advisories/GHSA-pwcw-6f5g-gxf8">CVE</a>.</p>\n<p>This release introduces a breaking changes to Helm:</p>\n<ul>\n<li>When using the <code>helm</code> client for the <code>template</code>, <code>install</code>, and <code>upgrade</code> commands there is a new flag. <code>--enable-dns</code> needs to be set for the <code>getHostByName</code> template function to attempt to lookup an IP address for a given hostname. If the flag is not set the template function will return an empty string and skip looping up an IP address for the host.</li>\n<li>The Helm SDK has added the <code>EnableDNS</code> property to the install action, the upgrade action, and the <code>Engine</code>. This property must be set to true for the in order for the <code>getHostByName</code> template function to attempt to lookup an IP address.</li>\n</ul>\n<p>The default for both of these cases is false.</p>\n<p><a href="https://github.com/phil9909">Philipp Stehle</a> at SAP disclosed the vulnerability to the Helm project.</p>\n<h2>Installation and Upgrading</h2>\n<p>Download Helm v3.11.1. The common platform binaries are here:</p>\n<ul>\n<li><a href="https://get.helm.sh/helm-v3.11.1-darwin-amd64.tar.gz" rel="nofollow">MacOS amd64</a> (<a href="https://get.helm.sh/helm-v3.11.1-darwin-amd64.tar.gz.sha256sum" rel="nofollow">checksum</a> / 2548a90e5cc957ccc5016b47060665a9d2cd4d5b4d61dcc32f5de3144d103826)</li>\n<li><a href="https://get.helm.sh/helm-v3.11.1-darwin-arm64.tar.gz" rel="nofollow">MacOS arm64</a> (<a href="https://get.helm.sh/helm-v3.11.1-darwin-arm64.tar.gz.sha256sum" rel="nofollow">checksum</a> / 43d0198a7a2ea2639caafa81bb0596c97bee2d4e40df50b36202343eb4d5c46b)</li>\n<li><a href="https://get.helm.sh/helm-v3.11.1-linux-amd64.tar.gz" rel="nofollow">Linux amd64</a> (<a href="https://get.helm.sh/helm-v3.11.1-linux-amd64.tar.gz.sha256sum" rel="nofollow">checksum</a> / 0b1be96b66fab4770526f136f5f1a385a47c41923d33aab0dcb500e0f6c1bf7c)</li>\n<li><a href="https://get.helm.sh/helm-v3.11.1-linux-arm.tar.gz" rel="nofollow">Linux arm</a> (<a href="https://get.helm.sh/helm-v3.11.1-linux-arm.tar.gz.sha256sum" rel="nofollow">checksum</a> / 77b797134ea9a121f2ede9d159a43a8b3895a9ff92cc24b71b77fb726d9eba6d)</li>\n<li><a href="https://get.helm.sh/helm-v3.11.1-linux-arm64.tar.gz" rel="nofollow">Linux arm64</a> (<a href="https://get.helm.sh/helm-v3.11.1-linux-arm64.tar.gz.sha256sum" rel="nofollow">checksum</a> / 919173e8fb7a3b54d76af9feb92e49e86d5a80c5185020bae8c393fa0f0de1e8)</li>\n<li><a href="https://get.helm.sh/helm-v3.11.1-linux-386.tar.gz" rel="nofollow">Linux i386</a> (<a href="https://get.helm.sh/helm-v3.11.1-linux-386.tar.gz.sha256sum" rel="nofollow">checksum</a> / 1581a4ce9d0014c49a3b2c6421f048d5c600e8cceced636eb4559073c335af0b)</li>\n<li><a href="https://get.helm.sh/helm-v3.11.1-linux-ppc64le.tar.gz" rel="nofollow">Linux ppc64le</a> (<a href="https://get.helm.sh/helm-v3.11.1-linux-ppc64le.tar.gz.sha256sum" rel="nofollow">checksum</a> / 6ab8f2e253c115b17eda1e10e96d1637047efd315e9807bcb1d0d0bcad278ab7)</li>\n<li><a href="https://get.helm.sh/helm-v3.11.1-linux-s390x.tar.gz" rel="nofollow">Linux s390x</a> (<a href="https://get.helm.sh/helm-v3.11.1-linux-s390x.tar.gz.sha256sum" rel="nofollow">checksum</a> / ab133e6b709c8107dc4f8f62838947350adb8e23d76b8c2c592ff4c09bc956ef)</li>\n<li><a href="https://get.helm.sh/helm-v3.11.1-windows-amd64.zip" rel="nofollow">Windows amd64</a> (<a href="https://get.helm.sh/helm-v3.11.1-windows-amd64.zip.sha256sum" rel="nofollow">checksum</a> / bc37d5d283e57c5dfa94f92ff704c8e273599ff8df3f8132cef5ca73f6a23d0a)</li>\n</ul>\n<p>This release was signed with <code>672C 657B E06B 4B30 969C 4A57 4614 49C2 5E36 B98E </code> and can be found at <a class="user-mention notranslate" href="https://github.com/mattfarina">@mattfarina</a> <a href="https://keybase.io/mattfarina" rel="nofollow">keybase account</a>. Please use the attached signatures for verifying this release using <code>gpg</code>.</p>\n<p>The <a href="https://helm.sh/docs/intro/quickstart/" rel="nofollow">Quickstart Guide</a> will get you going from there. For <strong>upgrade instructions</strong> or detailed installation notes, check the <a href="https://helm.sh/docs/intro/install/" rel="nofollow">install guide</a>. You can also use a <a href="https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3" rel="nofollow">script to install</a> on any system with <code>bash</code>.</p>\n<h2>What\'s Next</h2>\n<ul>\n<li>3.11.2 is the next patch/bug fix release and will be on March 08, 2023.</li>\n<li>3.12.0 is the next feature release and be on May 10, 2023.</li>\n</ul>',
'link': 'https://github.com/helm/helm/releases/tag/v3.11.1'
```

Constraint

- Cannot filter pre-releases as there is no identifier within entry to distinguish release types
    - Requires Gitlab API

raw sample rss entry

```bash
{
'id': 'tag:github.com,2008:Repository/43723161/v3.11.1', 
'guidislink': True, 
'link': 'https://github.com/helm/helm/releases/tag/v3.11.1', 
'updated': '2023-02-16T20:36:58Z', 
'updated_parsed': 
		time.struct_time(
				tm_year=2023, 
				tm_mon=2, 
				tm_mday=16, 
				tm_hour=20, 
				tm_min=36, 
				tm_sec=58, 
				tm_wday=3, 
				tm_yday=47, 
				tm_isdst=0), 
'links': [
	{'rel': 'alternate', 'type': 'text/html', 
		'href': 'https://github.com/helm/helm/releases/tag/v3.11.1'}
], 
'title': 'Helm v3.11.1', 
'title_detail': 
		{'type': 'text/plain', 
			'language': 'en-US', 
			'base': 'https://github.com/helm/helm/releases.atom', 
			'value': 'Helm v3.11.1'
		}, 
'content': [
		{'type': 'text/html', 
			'language': 'en-US', 
			'base': 'https://github.com/helm/helm/releases.atom', 
			'value': '<p>Helm v3.11.1 is a security (patch) release. Users are strongly recommended to update to this release.</p>\n<p>The template function <code>getHostByName</code> can be used to disclose information. More details are available in the <a href="https://github.com/helm/helm/security/advisories/GHSA-pwcw-6f5g-gxf8">CVE</a>.</p>\n<p>This release introduces a breaking changes to Helm:</p>\n<ul>\n<li>When using the <code>helm</code> client for the <code>template</code>, <code>install</code>, and <code>upgrade</code> commands there is a new flag. <code>--enable-dns</code> needs to be set for the <code>getHostByName</code> template function to attempt to lookup an IP address for a given hostname. If the flag is not set the template function will return an empty string and skip looping up an IP address for the host.</li>\n<li>The Helm SDK has added the <code>EnableDNS</code> property to the install action, the upgrade action, and the <code>Engine</code>. This property must be set to true for the in order for the <code>getHostByName</code> template function to attempt to lookup an IP address.</li>\n</ul>\n<p>The default for both of these cases is false.</p>\n<p><a href="https://github.com/phil9909">Philipp Stehle</a> at SAP disclosed the vulnerability to the Helm project.</p>\n<h2>Installation and Upgrading</h2>\n<p>Download Helm v3.11.1. The common platform binaries are here:</p>\n<ul>\n<li><a href="https://get.helm.sh/helm-v3.11.1-darwin-amd64.tar.gz" rel="nofollow">MacOS amd64</a> (<a href="https://get.helm.sh/helm-v3.11.1-darwin-amd64.tar.gz.sha256sum" rel="nofollow">checksum</a> / 2548a90e5cc957ccc5016b47060665a9d2cd4d5b4d61dcc32f5de3144d103826)</li>\n<li><a href="https://get.helm.sh/helm-v3.11.1-darwin-arm64.tar.gz" rel="nofollow">MacOS arm64</a> (<a href="https://get.helm.sh/helm-v3.11.1-darwin-arm64.tar.gz.sha256sum" rel="nofollow">checksum</a> / 43d0198a7a2ea2639caafa81bb0596c97bee2d4e40df50b36202343eb4d5c46b)</li>\n<li><a href="https://get.helm.sh/helm-v3.11.1-linux-amd64.tar.gz" rel="nofollow">Linux amd64</a> (<a href="https://get.helm.sh/helm-v3.11.1-linux-amd64.tar.gz.sha256sum" rel="nofollow">checksum</a> / 0b1be96b66fab4770526f136f5f1a385a47c41923d33aab0dcb500e0f6c1bf7c)</li>\n<li><a href="https://get.helm.sh/helm-v3.11.1-linux-arm.tar.gz" rel="nofollow">Linux arm</a> (<a href="https://get.helm.sh/helm-v3.11.1-linux-arm.tar.gz.sha256sum" rel="nofollow">checksum</a> / 77b797134ea9a121f2ede9d159a43a8b3895a9ff92cc24b71b77fb726d9eba6d)</li>\n<li><a href="https://get.helm.sh/helm-v3.11.1-linux-arm64.tar.gz" rel="nofollow">Linux arm64</a> (<a href="https://get.helm.sh/helm-v3.11.1-linux-arm64.tar.gz.sha256sum" rel="nofollow">checksum</a> / 919173e8fb7a3b54d76af9feb92e49e86d5a80c5185020bae8c393fa0f0de1e8)</li>\n<li><a href="https://get.helm.sh/helm-v3.11.1-linux-386.tar.gz" rel="nofollow">Linux i386</a> (<a href="https://get.helm.sh/helm-v3.11.1-linux-386.tar.gz.sha256sum" rel="nofollow">checksum</a> / 1581a4ce9d0014c49a3b2c6421f048d5c600e8cceced636eb4559073c335af0b)</li>\n<li><a href="https://get.helm.sh/helm-v3.11.1-linux-ppc64le.tar.gz" rel="nofollow">Linux ppc64le</a> (<a href="https://get.helm.sh/helm-v3.11.1-linux-ppc64le.tar.gz.sha256sum" rel="nofollow">checksum</a> / 6ab8f2e253c115b17eda1e10e96d1637047efd315e9807bcb1d0d0bcad278ab7)</li>\n<li><a href="https://get.helm.sh/helm-v3.11.1-linux-s390x.tar.gz" rel="nofollow">Linux s390x</a> (<a href="https://get.helm.sh/helm-v3.11.1-linux-s390x.tar.gz.sha256sum" rel="nofollow">checksum</a> / ab133e6b709c8107dc4f8f62838947350adb8e23d76b8c2c592ff4c09bc956ef)</li>\n<li><a href="https://get.helm.sh/helm-v3.11.1-windows-amd64.zip" rel="nofollow">Windows amd64</a> (<a href="https://get.helm.sh/helm-v3.11.1-windows-amd64.zip.sha256sum" rel="nofollow">checksum</a> / bc37d5d283e57c5dfa94f92ff704c8e273599ff8df3f8132cef5ca73f6a23d0a)</li>\n</ul>\n<p>This release was signed with <code>672C 657B E06B 4B30 969C 4A57 4614 49C2 5E36 B98E </code> and can be found at <a class="user-mention notranslate" href="https://github.com/mattfarina">@mattfarina</a> <a href="https://keybase.io/mattfarina" rel="nofollow">keybase account</a>. Please use the attached signatures for verifying this release using <code>gpg</code>.</p>\n<p>The <a href="https://helm.sh/docs/intro/quickstart/" rel="nofollow">Quickstart Guide</a> will get you going from there. For <strong>upgrade instructions</strong> or detailed installation notes, check the <a href="https://helm.sh/docs/intro/install/" rel="nofollow">install guide</a>. You can also use a <a href="https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3" rel="nofollow">script to install</a> on any system with <code>bash</code>.</p>\n<h2>What\'s Next</h2>\n<ul>\n<li>3.11.2 is the next patch/bug fix release and will be on March 08, 2023.</li>\n<li>3.12.0 is the next feature release and be on May 10, 2023.</li>\n</ul>'}
], 
'summary': '<p>Helm v3.11.1 is a security (patch) release. Users are strongly recommended to update to this release.</p>\n<p>The template function <code>getHostByName</code> can be used to disclose information. More details are available in the <a href="https://github.com/helm/helm/security/advisories/GHSA-pwcw-6f5g-gxf8">CVE</a>.</p>\n<p>This release introduces a breaking changes to Helm:</p>\n<ul>\n<li>When using the <code>helm</code> client for the <code>template</code>, <code>install</code>, and <code>upgrade</code> commands there is a new flag. <code>--enable-dns</code> needs to be set for the <code>getHostByName</code> template function to attempt to lookup an IP address for a given hostname. If the flag is not set the template function will return an empty string and skip looping up an IP address for the host.</li>\n<li>The Helm SDK has added the <code>EnableDNS</code> property to the install action, the upgrade action, and the <code>Engine</code>. This property must be set to true for the in order for the <code>getHostByName</code> template function to attempt to lookup an IP address.</li>\n</ul>\n<p>The default for both of these cases is false.</p>\n<p><a href="https://github.com/phil9909">Philipp Stehle</a> at SAP disclosed the vulnerability to the Helm project.</p>\n<h2>Installation and Upgrading</h2>\n<p>Download Helm v3.11.1. The common platform binaries are here:</p>\n<ul>\n<li><a href="https://get.helm.sh/helm-v3.11.1-darwin-amd64.tar.gz" rel="nofollow">MacOS amd64</a> (<a href="https://get.helm.sh/helm-v3.11.1-darwin-amd64.tar.gz.sha256sum" rel="nofollow">checksum</a> / 2548a90e5cc957ccc5016b47060665a9d2cd4d5b4d61dcc32f5de3144d103826)</li>\n<li><a href="https://get.helm.sh/helm-v3.11.1-darwin-arm64.tar.gz" rel="nofollow">MacOS arm64</a> (<a href="https://get.helm.sh/helm-v3.11.1-darwin-arm64.tar.gz.sha256sum" rel="nofollow">checksum</a> / 43d0198a7a2ea2639caafa81bb0596c97bee2d4e40df50b36202343eb4d5c46b)</li>\n<li><a href="https://get.helm.sh/helm-v3.11.1-linux-amd64.tar.gz" rel="nofollow">Linux amd64</a> (<a href="https://get.helm.sh/helm-v3.11.1-linux-amd64.tar.gz.sha256sum" rel="nofollow">checksum</a> / 0b1be96b66fab4770526f136f5f1a385a47c41923d33aab0dcb500e0f6c1bf7c)</li>\n<li><a href="https://get.helm.sh/helm-v3.11.1-linux-arm.tar.gz" rel="nofollow">Linux arm</a> (<a href="https://get.helm.sh/helm-v3.11.1-linux-arm.tar.gz.sha256sum" rel="nofollow">checksum</a> / 77b797134ea9a121f2ede9d159a43a8b3895a9ff92cc24b71b77fb726d9eba6d)</li>\n<li><a href="https://get.helm.sh/helm-v3.11.1-linux-arm64.tar.gz" rel="nofollow">Linux arm64</a> (<a href="https://get.helm.sh/helm-v3.11.1-linux-arm64.tar.gz.sha256sum" rel="nofollow">checksum</a> / 919173e8fb7a3b54d76af9feb92e49e86d5a80c5185020bae8c393fa0f0de1e8)</li>\n<li><a href="https://get.helm.sh/helm-v3.11.1-linux-386.tar.gz" rel="nofollow">Linux i386</a> (<a href="https://get.helm.sh/helm-v3.11.1-linux-386.tar.gz.sha256sum" rel="nofollow">checksum</a> / 1581a4ce9d0014c49a3b2c6421f048d5c600e8cceced636eb4559073c335af0b)</li>\n<li><a href="https://get.helm.sh/helm-v3.11.1-linux-ppc64le.tar.gz" rel="nofollow">Linux ppc64le</a> (<a href="https://get.helm.sh/helm-v3.11.1-linux-ppc64le.tar.gz.sha256sum" rel="nofollow">checksum</a> / 6ab8f2e253c115b17eda1e10e96d1637047efd315e9807bcb1d0d0bcad278ab7)</li>\n<li><a href="https://get.helm.sh/helm-v3.11.1-linux-s390x.tar.gz" rel="nofollow">Linux s390x</a> (<a href="https://get.helm.sh/helm-v3.11.1-linux-s390x.tar.gz.sha256sum" rel="nofollow">checksum</a> / ab133e6b709c8107dc4f8f62838947350adb8e23d76b8c2c592ff4c09bc956ef)</li>\n<li><a href="https://get.helm.sh/helm-v3.11.1-windows-amd64.zip" rel="nofollow">Windows amd64</a> (<a href="https://get.helm.sh/helm-v3.11.1-windows-amd64.zip.sha256sum" rel="nofollow">checksum</a> / bc37d5d283e57c5dfa94f92ff704c8e273599ff8df3f8132cef5ca73f6a23d0a)</li>\n</ul>\n<p>This release was signed with <code>672C 657B E06B 4B30 969C 4A57 4614 49C2 5E36 B98E </code> and can be found at <a class="user-mention notranslate" href="https://github.com/mattfarina">@mattfarina</a> <a href="https://keybase.io/mattfarina" rel="nofollow">keybase account</a>. Please use the attached signatures for verifying this release using <code>gpg</code>.</p>\n<p>The <a href="https://helm.sh/docs/intro/quickstart/" rel="nofollow">Quickstart Guide</a> will get you going from there. For <strong>upgrade instructions</strong> or detailed installation notes, check the <a href="https://helm.sh/docs/intro/install/" rel="nofollow">install guide</a>. You can also use a <a href="https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3" rel="nofollow">script to install</a> on any system with <code>bash</code>.</p>\n<h2>What\'s Next</h2>\n<ul>\n<li>3.11.2 is the next patch/bug fix release and will be on March 08, 2023.</li>\n<li>3.12.0 is the next feature release and be on May 10, 2023.</li>\n</ul>', 
'authors': [{'name': 'mattfarina'}], 
'author_detail': {'name': 'mattfarina'}, 
'author': 'mattfarina', 
'media_thumbnail': [
	{'height': '30', 'width': '30', 'url': 'https://avatars.githubusercontent.com/u/62991?s=60&v=4'}
], 
'href': ''
}
```

## # Gitlab Runner Images

## AWS Cli Feed

URL

```bash
https://github.com/aws/aws-cli/tags.atom
```

Key components

```bash
'title': '1.27.76',
'updated': '2023-02-21T20:12:36Z', 

'link': 'https://github.com/aws/aws-cli/releases/tag/1.27.76'
```

Constraint

- Summary param does not provide information about the version update
- Cannot filter pre-releases as there is no identifier within entry to distinguish release types
    - Requires Gitlab API

raw sample rss entry

```bash
{
'id': 'tag:github.com,2008:Repository/6780767/1.27.76', 
'guidislink': True, 
'link': 'https://github.com/aws/aws-cli/releases/tag/1.27.76', 
'updated': '2023-02-21T20:12:36Z', 
'updated_parsed': 
		time.struct_time(
				tm_year=2023, 
				tm_mon=2, 
				tm_mday=21, 
				tm_hour=20, 
				tm_min=12, 
				tm_sec=36, 
				tm_wday=1, 
				tm_yday=52, 
				tm_isdst=0), 
'links': [
		{'rel': 'alternate', 'type': 'text/html', 
			'href': 'https://github.com/aws/aws-cli/releases/tag/1.27.76'}
], 
'title': '1.27.76', 
'title_detail': 
		{'type': 'text/plain', 
			'language': 'en-US', 
			'base': 'https://github.com/aws/aws-cli/tags.atom', 
			'value': '1.27.76'}, 
'content': [
		{'type': 'text/plain', 'language': 'en-US', 
			'base': 'https://github.com/aws/aws-cli/tags.atom', 'value': ''}
], 'summary': '', 
'authors': [{'name': 'aws-sdk-python-automation'}], 
'author_detail': {'name': 'aws-sdk-python-automation'}, 
'author': 'aws-sdk-python-automation', 
'media_thumbnail': [
		{'height': '30', 'width': '30', 'url': 'https://avatars.githubusercontent.com/u/43144185?s=60&v=4'}
], 
'href': ''
}
```

## Correto 11 Feed

URL

```bash
https://github.com/corretto/corretto-11/releases.atom
```

Key components

```bash
'title': '11.0.18.11.1', 
'updated': '2023-02-02T23:02:54Z', 
'summary': '<p>For release notes see : <a href="https://github.com/corretto/corretto-11/blob/release-11.0.18.11.1/CHANGELOG.md">CHANGELOG.md</a></p>\n<table>\n<thead>\n<tr>\n<th>Platform</th>\n<th>Type</th>\n<th>Download Link</th>\n<th>Checksum (MD5) / Checksum (SHA256)</th>\n<th>Sig File</th>\n</tr>\n</thead>\n<tbody>\n<tr>\n<td><a href="https://docs.aws.amazon.com/corretto/latest/corretto-11-ug/generic-linux-install.html" rel="nofollow">Alpine Linux aarch64</a> (preview)</td>\n<td>JDK</td>\n<td><a href="https://corretto.aws/downloads/resources/11.0.18.11.1/amazon-corretto-11.0.18.11.1-alpine-linux-aarch64.tar.gz" rel="nofollow">amazon-corretto-11.0.18.11.1-alpine-linux-aarch64.tar.gz</a></td>\n<td><code>9b2de5cfae8e5263861eab99aa079210</code> /<br /> <code>c047640badcbb2ccca82237cd6ed7e514c5177ccf5102a4d1fe6c237153dee73</code></td>\n<td><a href="https://corretto.aws/downloads/resources/11.0.18.11.1/amazon-corretto-11.0.18.11.1-alpine-linux-aarch64.tar.gz.sig" rel="nofollow">Download</a></td>\n</tr>\n</tbody>\n</table>', 
'link': 'https://github.com/corretto/corretto-11/releases/tag/11.0.18.11.1'
```

Constraint

- Cannot filter pre-releases as there is no identifier within entry to distinguish release types
    - Requires Gitlab API

raw sample rss entry

```bash
{
'id': 'tag:github.com,2008:Repository/170194909/11.0.18.11.1', 
'guidislink': True, 
'link': 'https://github.com/corretto/corretto-11/releases/tag/11.0.18.11.1', 
'updated': '2023-02-02T23:02:54Z', 
'updated_parsed': 
		time.struct_time(tm_year=2023, 
				tm_mon=2, 
				tm_mday=2, 
				tm_hour=23, 
				tm_min=2, 
				tm_sec=54, 
				tm_wday=3, 
				tm_yday=33, 
				tm_isdst=0), 
'links': [
		{'rel': 'alternate', 'type': 'text/html', 
			'href': 'https://github.com/corretto/corretto-11/releases/tag/11.0.18.11.1'}
], 
'title': '11.0.18.11.1', 
'title_detail': 
		{'type': 'text/plain', 
			'language': 'en-US', 
			'base': 'https://github.com/corretto/corretto-11/releases.atom', 
			'value': '11.0.18.11.1'}, 
'content': [
		{'type': 'text/html', 'language': 'en-US', 
			'base': 'https://github.com/corretto/corretto-11/releases.atom', 
			'value': '<p>For release notes see : <a href="https://github.com/corretto/corretto-11/blob/release-11.0.18.11.1/CHANGELOG.md">CHANGELOG.md</a></p>\n<table>\n<thead>\n<tr>\n<th>Platform</th>\n<th>Type</th>\n<th>Download Link</th>\n<th>Checksum (MD5) / Checksum (SHA256)</th>\n<th>Sig File</th>\n</tr>\n</thead>\n<tbody>\n<tr>\n<td><a href="https://docs.aws.amazon.com/corretto/latest/corretto-11-ug/generic-linux-install.html" rel="nofollow">Alpine Linux aarch64</a> (preview)</td>\n<td>JDK</td>\n<td><a href="https://corretto.aws/downloads/resources/11.0.18.11.1/amazon-corretto-11.0.18.11.1-alpine-linux-aarch64.tar.gz" rel="nofollow">amazon-corretto-11.0.18.11.1-alpine-linux-aarch64.tar.gz</a></td>\n<td><code>9b2de5cfae8e5263861eab99aa079210</code> /<br /> <code>c047640badcbb2ccca82237cd6ed7e514c5177ccf5102a4d1fe6c237153dee73</code></td>\n<td><a href="https://corretto.aws/downloads/resources/11.0.18.11.1/amazon-corretto-11.0.18.11.1-alpine-linux-aarch64.tar.gz.sig" rel="nofollow">Download</a></td>\n</tr>\n</tbody>\n</table>'}
], 
'summary': '<p>For release notes see : <a href="https://github.com/corretto/corretto-11/blob/release-11.0.18.11.1/CHANGELOG.md">CHANGELOG.md</a></p>\n<table>\n<thead>\n<tr>\n<th>Platform</th>\n<th>Type</th>\n<th>Download Link</th>\n<th>Checksum (MD5) / Checksum (SHA256)</th>\n<th>Sig File</th>\n</tr>\n</thead>\n<tbody>\n<tr>\n<td><a href="https://docs.aws.amazon.com/corretto/latest/corretto-11-ug/generic-linux-install.html" rel="nofollow">Alpine Linux aarch64</a> (preview)</td>\n<td>JDK</td>\n<td><a href="https://corretto.aws/downloads/resources/11.0.18.11.1/amazon-corretto-11.0.18.11.1-alpine-linux-aarch64.tar.gz" rel="nofollow">amazon-corretto-11.0.18.11.1-alpine-linux-aarch64.tar.gz</a></td>\n<td><code>9b2de5cfae8e5263861eab99aa079210</code> /<br /> <code>c047640badcbb2ccca82237cd6ed7e514c5177ccf5102a4d1fe6c237153dee73</code></td>\n<td><a href="https://corretto.aws/downloads/resources/11.0.18.11.1/amazon-corretto-11.0.18.11.1-alpine-linux-aarch64.tar.gz.sig" rel="nofollow">Download</a></td>\n</tr>\n</tbody>\n</table>', 
'authors': [{'name': 'benty-amzn'}], 
'author_detail': {'name': 'benty-amzn'}, 
'author': 'benty-amzn', 
'media_thumbnail': [
		{'height': '30', 'width': '30', 'url': 'https://avatars.githubusercontent.com/u/61255184?s=60&v=4'}
], 
'href': ''
}
```

## Correto 17 Feed

URL

```bash
https://github.com/corretto/corretto-17/releases.atom
```

Key components

```bash
'title': '17.0.6.10.1', 
'updated': '2023-02-02T23:03:36Z',
'link': 'https://github.com/corretto/corretto-17/releases/tag/17.0.6.10.1', 
'summary': '<p>For release notes see : <a href="https://github.com/corretto/corretto-17/blob/release-17.0.6.10.1/CHANGELOG.md">CHANGELOG.md</a></p>\n<table>\n<thead>\n<tr>\n<th>Platform</th>\n<th>Type</th>\n<th>Download Link</th>\n<th>Checksum (MD5) / Checksum (SHA256)</th>\n<th>Sig File</th>\n</tr>\n</thead>\n<tbody>\n<tr>\n<td><a href="https://docs.aws.amazon.com/corretto/latest/corretto-17-ug/generic-linux-install.html" rel="nofollow">Linux x64</a></td>\n<td>JDK</td>\n<td><a href="https://corretto.aws/downloads/resources/17.0.6.10.1/java-17-amazon-corretto-jdk_17.0.6.10-1_amd64.deb" rel="nofollow">java-17-amazon-corretto-jdk_17.0.6.10-1_amd64.deb</a></td>\n<td><code>025505ee141db2a78670e2c51e1f3b5a</code> /<br /> <code>501e9f58ed19f966b4ed95623755e96c91a275244be4fca21afff2bfeaba7d14</code></td>\n<td></td>\n</tr>\n<tr>\n<td><a href="https://docs.aws.amazon.com/corretto/latest/corretto-17-ug/generic-linux-install.html" rel="nofollow">Linux x64</a></td>\n<td>JDK</td>\n<td><a href="https://corretto.aws/downloads/resources/17.0.6.10.1/java-17-amazon-corretto-devel-17.0.6.10-1.x86_64.rpm" rel="nofollow">java-17-amazon-corretto-devel-17.0.6.10-1.x86_64.rpm</a></td>\n<td><code>dd1bf75f6aa3360d312890996a5071c1</code> /<br /> <code>bcb76d3bd1f3d61c8047f929ee93b47da87f21afd4a2dee2158c09f183492e74</code></td>\n<td></td>\n</tr>\n<tr>\n<td><a href="https://docs.aws.amazon.com/corretto/latest/corretto-17-ug/generic-linux-install.html" rel="nofollow">Linux x64</a></td>\n<td>JDK</td>\n<td><a href="https://corretto.aws/downloads/resources/17.0.6.10.1/amazon-corretto-17.0.6.10.1-linux-x64.tar.gz" rel="nofollow">amazon-corretto-17.0.6.10.1-linux-x64.tar.gz</a></td>\n<td><code>50c8e341384a04b95cd1c8b698116dab</code> /<br /> <code>365bb4ae3f56bfb3c0df5f8f5b809ff0212366c46970c4b371acb80ecf4706cc</code></td>\n<td><a href="https://corretto.aws/downloads/resources/17.0.6.10.1/amazon-corretto-17.0.6.10.1-linux-x64.tar.gz.sig" rel="nofollow">Download</a></td>\n</tr>\n<tr>\n<td><a href="https://docs.aws.amazon.com/corretto/latest/corretto-17-ug/generic-linux-install.html" rel="nofollow">Linux aarch64</a></td>\n<td>JDK</td>\n<td><a href="https://corretto.aws/downloads/resources/17.0.6.10.1/java-17-amazon-corretto-jdk_17.0.6.10-1_arm64.deb" rel="nofollow">java-17-amazon-corretto-jdk_17.0.6.10-1_arm64.deb</a></td>\n<td><code>75acc3e7f135ad2d00d38a8732aa1b00</code> /<br /> <code>482f561086b4c360c33f246c87c95aeea9fbd0fdc1b540d4e504868afb262d5f</code></td>\n<td></td>\n</tr>\n<tr>\n<td><a href="https://docs.aws.amazon.com/corretto/latest/corretto-17-ug/generic-linux-install.html" rel="nofollow">Linux aarch64</a></td>\n<td>JDK</td>\n<td><a href="https://corretto.aws/downloads/resources/17.0.6.10.1/java-17-amazon-corretto-devel-17.0.6.10-1.aarch64.rpm" rel="nofollow">java-17-amazon-corretto-devel-17.0.6.10-1.aarch64.rpm</a></td>\n<td><code>4a69d896c403a1a3807627fb28dec76f</code> /<br /> <code>069ac8b950a91c24369703d67cf1e900097383ba1f053ac05a31bc6676ae9c35</code></td>\n<td></td>\n</tr>\n<tr>\n<td><a href="https://docs.aws.amazon.com/corretto/latest/corretto-17-ug/generic-linux-install.html" rel="nofollow">Linux aarch64</a></td>\n<td>JDK</td>\n<td><a href="https://corretto.aws/downloads/resources/17.0.6.10.1/amazon-corretto-17.0.6.10.1-linux-aarch64.tar.gz" rel="nofollow">amazon-corretto-17.0.6.10.1-linux-aarch64.tar.gz</a></td>\n<td><code>25be86e6a0b3cd7c56624e87cb0692d4</code> /<br /> <code>8fc36009858cfb4dbd30ba4847c6fc4d53d4f843b08dea8189f38fbf8bf40ca8</code></td>\n<td><a href="https://corretto.aws/downloads/resources/17.0.6.10.1/amazon-corretto-17.0.6.10.1-linux-aarch64.tar.gz.sig" rel="nofollow">Download</a></td>\n</tr>\n<tr>\n<td><a href="https://docs.aws.amazon.com/corretto/latest/corretto-17-ug/windows-7-install.html" rel="nofollow">Windows x64</a></td>\n<td>JDK</td>\n<td><a href="https://corretto.aws/downloads/resources/17.0.6.10.1/amazon-corretto-17.0.6.10.1-windows-x64.msi" rel="nofollow">amazon-corretto-17.0.6.10.1-windows-x64.msi</a></td>\n<td><code>1ae096ae7e62bdd28bf0e360e31ccff8</code> /<br /> <code>a2ac2df53ae6b7d0a155cdd29897701671a028a74e7f48f7e4489610589eac29</code></td>\n<td></td>\n</tr>\n<tr>\n<td><a href="https://docs.aws.amazon.com/corretto/latest/corretto-17-ug/windows-7-install.html" rel="nofollow">Windows x64</a></td>\n<td>JDK</td>\n<td><a href="https://corretto.aws/downloads/resources/17.0.6.10.1/amazon-corretto-17.0.6.10.1-windows-x64-jdk.zip" rel="nofollow">amazon-corretto-17.0.6.10.1-windows-x64-jdk.zip</a></td>\n<td><code>478628efdf21bba10b1f909cefb9e413</code> /<br /> <code>27dfa7189763bf5bee6250baef22bb6f6032deebe0edd11f79495781cc7955fe</code></td>\n<td><a href="https://corretto.aws/downloads/resources/17.0.6.10.1/amazon-corretto-17.0.6.10.1-windows-x64-jdk.zip.sig" rel="nofollow">Download</a></td>\n</tr>\n<tr>\n<td><a href="https://docs.aws.amazon.com/corretto/latest/corretto-17-ug/macos-install.html" rel="nofollow">macOS x64</a></td>\n<td>JDK</td>\n<td><a href="https://corretto.aws/downloads/resources/17.0.6.10.1/amazon-corretto-17.0.6.10.1-macosx-x64.pkg" rel="nofollow">amazon-corretto-17.0.6.10.1-macosx-x64.pkg</a></td>\n<td><code>4d6a3d571c4f718f7e268fa27bf7252e</code> /<br /> <code>4de291b2c5e4535fce01a8ced0416424352d2d320794087f62c3a6fd42a3ab0f</code></td>\n<td></td>\n</tr>\n<tr>\n<td><a href="https://docs.aws.amazon.com/corretto/latest/corretto-17-ug/macos-install.html" rel="nofollow">macOS x64</a></td>\n<td>JDK</td>\n<td><a href="https://corretto.aws/downloads/resources/17.0.6.10.1/amazon-corretto-17.0.6.10.1-macosx-x64.tar.gz" rel="nofollow">amazon-corretto-17.0.6.10.1-macosx-x64.tar.gz</a></td>\n<td><code>fe0f0a346c7108f4b70e01bdbd27317c</code> /<br /> <code>1ba7e50d74c2f402431d365eb8e5f7b860b03b18956af59f5f364f6567a8463e</code></td>\n<td><a href="https://corretto.aws/downloads/resources/17.0.6.10.1/amazon-corretto-17.0.6.10.1-macosx-x64.tar.gz.sig" rel="nofollow">Download</a></td>\n</tr>\n<tr>\n<td><a href="https://docs.aws.amazon.com/corretto/latest/corretto-17-ug/macos-install.html" rel="nofollow">macOS aarch64</a></td>\n<td>JDK</td>\n<td><a href="https://corretto.aws/downloads/resources/17.0.6.10.1/amazon-corretto-17.0.6.10.1-macosx-aarch64.pkg" rel="nofollow">amazon-corretto-17.0.6.10.1-macosx-aarch64.pkg</a></td>\n<td><code>28e1c13fe099fd28dc22963b36a18bd5</code> /<br /> <code>526d2f664bc5d93aeff6b5d8e1b45d9d644d09b1939bcabbe04cdf692c1f2db2</code></td>\n<td></td>\n</tr>\n<tr>\n<td><a href="https://docs.aws.amazon.com/corretto/latest/corretto-17-ug/macos-install.html" rel="nofollow">macOS aarch64</a></td>\n<td>JDK</td>\n<td><a href="https://corretto.aws/downloads/resources/17.0.6.10.1/amazon-corretto-17.0.6.10.1-macosx-aarch64.tar.gz" rel="nofollow">amazon-corretto-17.0.6.10.1-macosx-aarch64.tar.gz</a></td>\n<td><code>7a0a13d88cb3d4d3901332be8a87d64a</code> /<br /> <code>f7411c1d8a94681e669b133ab57a7ef815aa145b3ecc041c93ca7ff1eb1811b3</code></td>\n<td><a href="https://corretto.aws/downloads/resources/17.0.6.10.1/amazon-corretto-17.0.6.10.1-macosx-aarch64.tar.gz.sig" rel="nofollow">Download</a></td>\n</tr>\n<tr>\n<td><a href="https://docs.aws.amazon.com/corretto/latest/corretto-17-ug/generic-linux-install.html" rel="nofollow">Alpine Linux x64</a></td>\n<td>JDK</td>\n<td><a href="https://corretto.aws/downloads/resources/17.0.6.10.1/amazon-corretto-17.0.6.10.1-alpine-linux-x64.tar.gz" rel="nofollow">amazon-corretto-17.0.6.10.1-alpine-linux-x64.tar.gz</a></td>\n<td><code>952ddd95dfa688f4bea15a87a0137f9e</code> /<br /> <code>49d2131a3fd23c13c429d4c666719e9859be9a389fec20605ce4ee706a7c6640</code></td>\n<td><a href="https://corretto.aws/downloads/resources/17.0.6.10.1/amazon-corretto-17.0.6.10.1-alpine-linux-x64.tar.gz.sig" rel="nofollow">Download</a></td>\n</tr>\n<tr>\n<td><a href="https://docs.aws.amazon.com/corretto/latest/corretto-17-ug/generic-linux-install.html" rel="nofollow">Alpine Linux aarch64</a> (preview)</td>\n<td>JDK</td>\n<td><a href="https://corretto.aws/downloads/resources/17.0.6.10.1/amazon-corretto-17.0.6.10.1-alpine-linux-aarch64.tar.gz" rel="nofollow">amazon-corretto-17.0.6.10.1-alpine-linux-aarch64.tar.gz</a></td>\n<td><code>82ddc39899d0b39ea4e452add5194108</code> /<br /> <code>4211f9e47ef23995dcff2b5f0193bad68837aaae20cf85756480cc9cf6cec127</code></td>\n<td><a href="https://corretto.aws/downloads/resources/17.0.6.10.1/amazon-corretto-17.0.6.10.1-alpine-linux-aarch64.tar.gz.sig" rel="nofollow">Download</a></td>\n</tr>\n</tbody>\n</table>',
```

Constraint

- Cannot filter pre-releases as there is no identifier within entry to distinguish release types
    - Requires Gitlab API

raw sample rss entry

```bash
{
'id': 'tag:github.com,2008:Repository/381428400/17.0.6.10.1', 
'guidislink': True, 
'link': 'https://github.com/corretto/corretto-17/releases/tag/17.0.6.10.1', 
'updated': '2023-02-02T23:03:36Z', 
'updated_parsed': 
		time.struct_time(
				tm_year=2023, 
				tm_mon=2, 
				tm_mday=2, 
				tm_hour=23, 
				tm_min=3, 
				tm_sec=36, 
				tm_wday=3, 
				tm_yday=33, 
				tm_isdst=0), 
'links': [
		{'rel': 'alternate', 'type': 'text/html', 
			'href': 'https://github.com/corretto/corretto-17/releases/tag/17.0.6.10.1'}
], 
'title': '17.0.6.10.1', 
'title_detail': 
		{'type': 'text/plain', 
			'language': 'en-US', 
			'base': 'https://github.com/corretto/corretto-17/releases.atom', 
			'value': '17.0.6.10.1'}, 
'content': [
		{'type': 'text/html', 'language': 'en-US', 
			'base': 'https://github.com/corretto/corretto-17/releases.atom', 
			'value': '<p>For release notes see : <a href="https://github.com/corretto/corretto-17/blob/release-17.0.6.10.1/CHANGELOG.md">CHANGELOG.md</a></p>\n<table>\n<thead>\n<tr>\n<th>Platform</th>\n<th>Type</th>\n<th>Download Link</th>\n<th>Checksum (MD5) / Checksum (SHA256)</th>\n<th>Sig File</th>\n</tr>\n</thead>\n<tbody>\n<tr>\n<td><a href="https://docs.aws.amazon.com/corretto/latest/corretto-17-ug/generic-linux-install.html" rel="nofollow">Linux x64</a></td>\n<td>JDK</td>\n<td><a href="https://corretto.aws/downloads/resources/17.0.6.10.1/java-17-amazon-corretto-jdk_17.0.6.10-1_amd64.deb" rel="nofollow">java-17-amazon-corretto-jdk_17.0.6.10-1_amd64.deb</a></td>\n<td><code>025505ee141db2a78670e2c51e1f3b5a</code> /<br /> <code>501e9f58ed19f966b4ed95623755e96c91a275244be4fca21afff2bfeaba7d14</code></td>\n<td></td>\n</tr>\n<tr>\n<td><a href="https://docs.aws.amazon.com/corretto/latest/corretto-17-ug/generic-linux-install.html" rel="nofollow">Linux x64</a></td>\n<td>JDK</td>\n<td><a href="https://corretto.aws/downloads/resources/17.0.6.10.1/java-17-amazon-corretto-devel-17.0.6.10-1.x86_64.rpm" rel="nofollow">java-17-amazon-corretto-devel-17.0.6.10-1.x86_64.rpm</a></td>\n<td><code>dd1bf75f6aa3360d312890996a5071c1</code> /<br /> <code>bcb76d3bd1f3d61c8047f929ee93b47da87f21afd4a2dee2158c09f183492e74</code></td>\n<td></td>\n</tr>\n<tr>\n<td><a href="https://docs.aws.amazon.com/corretto/latest/corretto-17-ug/generic-linux-install.html" rel="nofollow">Linux x64</a></td>\n<td>JDK</td>\n<td><a href="https://corretto.aws/downloads/resources/17.0.6.10.1/amazon-corretto-17.0.6.10.1-linux-x64.tar.gz" rel="nofollow">amazon-corretto-17.0.6.10.1-linux-x64.tar.gz</a></td>\n<td><code>50c8e341384a04b95cd1c8b698116dab</code> /<br /> <code>365bb4ae3f56bfb3c0df5f8f5b809ff0212366c46970c4b371acb80ecf4706cc</code></td>\n<td><a href="https://corretto.aws/downloads/resources/17.0.6.10.1/amazon-corretto-17.0.6.10.1-linux-x64.tar.gz.sig" rel="nofollow">Download</a></td>\n</tr>\n<tr>\n<td><a href="https://docs.aws.amazon.com/corretto/latest/corretto-17-ug/generic-linux-install.html" rel="nofollow">Linux aarch64</a></td>\n<td>JDK</td>\n<td><a href="https://corretto.aws/downloads/resources/17.0.6.10.1/java-17-amazon-corretto-jdk_17.0.6.10-1_arm64.deb" rel="nofollow">java-17-amazon-corretto-jdk_17.0.6.10-1_arm64.deb</a></td>\n<td><code>75acc3e7f135ad2d00d38a8732aa1b00</code> /<br /> <code>482f561086b4c360c33f246c87c95aeea9fbd0fdc1b540d4e504868afb262d5f</code></td>\n<td></td>\n</tr>\n<tr>\n<td><a href="https://docs.aws.amazon.com/corretto/latest/corretto-17-ug/generic-linux-install.html" rel="nofollow">Linux aarch64</a></td>\n<td>JDK</td>\n<td><a href="https://corretto.aws/downloads/resources/17.0.6.10.1/java-17-amazon-corretto-devel-17.0.6.10-1.aarch64.rpm" rel="nofollow">java-17-amazon-corretto-devel-17.0.6.10-1.aarch64.rpm</a></td>\n<td><code>4a69d896c403a1a3807627fb28dec76f</code> /<br /> <code>069ac8b950a91c24369703d67cf1e900097383ba1f053ac05a31bc6676ae9c35</code></td>\n<td></td>\n</tr>\n<tr>\n<td><a href="https://docs.aws.amazon.com/corretto/latest/corretto-17-ug/generic-linux-install.html" rel="nofollow">Linux aarch64</a></td>\n<td>JDK</td>\n<td><a href="https://corretto.aws/downloads/resources/17.0.6.10.1/amazon-corretto-17.0.6.10.1-linux-aarch64.tar.gz" rel="nofollow">amazon-corretto-17.0.6.10.1-linux-aarch64.tar.gz</a></td>\n<td><code>25be86e6a0b3cd7c56624e87cb0692d4</code> /<br /> <code>8fc36009858cfb4dbd30ba4847c6fc4d53d4f843b08dea8189f38fbf8bf40ca8</code></td>\n<td><a href="https://corretto.aws/downloads/resources/17.0.6.10.1/amazon-corretto-17.0.6.10.1-linux-aarch64.tar.gz.sig" rel="nofollow">Download</a></td>\n</tr>\n<tr>\n<td><a href="https://docs.aws.amazon.com/corretto/latest/corretto-17-ug/windows-7-install.html" rel="nofollow">Windows x64</a></td>\n<td>JDK</td>\n<td><a href="https://corretto.aws/downloads/resources/17.0.6.10.1/amazon-corretto-17.0.6.10.1-windows-x64.msi" rel="nofollow">amazon-corretto-17.0.6.10.1-windows-x64.msi</a></td>\n<td><code>1ae096ae7e62bdd28bf0e360e31ccff8</code> /<br /> <code>a2ac2df53ae6b7d0a155cdd29897701671a028a74e7f48f7e4489610589eac29</code></td>\n<td></td>\n</tr>\n<tr>\n<td><a href="https://docs.aws.amazon.com/corretto/latest/corretto-17-ug/windows-7-install.html" rel="nofollow">Windows x64</a></td>\n<td>JDK</td>\n<td><a href="https://corretto.aws/downloads/resources/17.0.6.10.1/amazon-corretto-17.0.6.10.1-windows-x64-jdk.zip" rel="nofollow">amazon-corretto-17.0.6.10.1-windows-x64-jdk.zip</a></td>\n<td><code>478628efdf21bba10b1f909cefb9e413</code> /<br /> <code>27dfa7189763bf5bee6250baef22bb6f6032deebe0edd11f79495781cc7955fe</code></td>\n<td><a href="https://corretto.aws/downloads/resources/17.0.6.10.1/amazon-corretto-17.0.6.10.1-windows-x64-jdk.zip.sig" rel="nofollow">Download</a></td>\n</tr>\n<tr>\n<td><a href="https://docs.aws.amazon.com/corretto/latest/corretto-17-ug/macos-install.html" rel="nofollow">macOS x64</a></td>\n<td>JDK</td>\n<td><a href="https://corretto.aws/downloads/resources/17.0.6.10.1/amazon-corretto-17.0.6.10.1-macosx-x64.pkg" rel="nofollow">amazon-corretto-17.0.6.10.1-macosx-x64.pkg</a></td>\n<td><code>4d6a3d571c4f718f7e268fa27bf7252e</code> /<br /> <code>4de291b2c5e4535fce01a8ced0416424352d2d320794087f62c3a6fd42a3ab0f</code></td>\n<td></td>\n</tr>\n<tr>\n<td><a href="https://docs.aws.amazon.com/corretto/latest/corretto-17-ug/macos-install.html" rel="nofollow">macOS x64</a></td>\n<td>JDK</td>\n<td><a href="https://corretto.aws/downloads/resources/17.0.6.10.1/amazon-corretto-17.0.6.10.1-macosx-x64.tar.gz" rel="nofollow">amazon-corretto-17.0.6.10.1-macosx-x64.tar.gz</a></td>\n<td><code>fe0f0a346c7108f4b70e01bdbd27317c</code> /<br /> <code>1ba7e50d74c2f402431d365eb8e5f7b860b03b18956af59f5f364f6567a8463e</code></td>\n<td><a href="https://corretto.aws/downloads/resources/17.0.6.10.1/amazon-corretto-17.0.6.10.1-macosx-x64.tar.gz.sig" rel="nofollow">Download</a></td>\n</tr>\n<tr>\n<td><a href="https://docs.aws.amazon.com/corretto/latest/corretto-17-ug/macos-install.html" rel="nofollow">macOS aarch64</a></td>\n<td>JDK</td>\n<td><a href="https://corretto.aws/downloads/resources/17.0.6.10.1/amazon-corretto-17.0.6.10.1-macosx-aarch64.pkg" rel="nofollow">amazon-corretto-17.0.6.10.1-macosx-aarch64.pkg</a></td>\n<td><code>28e1c13fe099fd28dc22963b36a18bd5</code> /<br /> <code>526d2f664bc5d93aeff6b5d8e1b45d9d644d09b1939bcabbe04cdf692c1f2db2</code></td>\n<td></td>\n</tr>\n<tr>\n<td><a href="https://docs.aws.amazon.com/corretto/latest/corretto-17-ug/macos-install.html" rel="nofollow">macOS aarch64</a></td>\n<td>JDK</td>\n<td><a href="https://corretto.aws/downloads/resources/17.0.6.10.1/amazon-corretto-17.0.6.10.1-macosx-aarch64.tar.gz" rel="nofollow">amazon-corretto-17.0.6.10.1-macosx-aarch64.tar.gz</a></td>\n<td><code>7a0a13d88cb3d4d3901332be8a87d64a</code> /<br /> <code>f7411c1d8a94681e669b133ab57a7ef815aa145b3ecc041c93ca7ff1eb1811b3</code></td>\n<td><a href="https://corretto.aws/downloads/resources/17.0.6.10.1/amazon-corretto-17.0.6.10.1-macosx-aarch64.tar.gz.sig" rel="nofollow">Download</a></td>\n</tr>\n<tr>\n<td><a href="https://docs.aws.amazon.com/corretto/latest/corretto-17-ug/generic-linux-install.html" rel="nofollow">Alpine Linux x64</a></td>\n<td>JDK</td>\n<td><a href="https://corretto.aws/downloads/resources/17.0.6.10.1/amazon-corretto-17.0.6.10.1-alpine-linux-x64.tar.gz" rel="nofollow">amazon-corretto-17.0.6.10.1-alpine-linux-x64.tar.gz</a></td>\n<td><code>952ddd95dfa688f4bea15a87a0137f9e</code> /<br /> <code>49d2131a3fd23c13c429d4c666719e9859be9a389fec20605ce4ee706a7c6640</code></td>\n<td><a href="https://corretto.aws/downloads/resources/17.0.6.10.1/amazon-corretto-17.0.6.10.1-alpine-linux-x64.tar.gz.sig" rel="nofollow">Download</a></td>\n</tr>\n<tr>\n<td><a href="https://docs.aws.amazon.com/corretto/latest/corretto-17-ug/generic-linux-install.html" rel="nofollow">Alpine Linux aarch64</a> (preview)</td>\n<td>JDK</td>\n<td><a href="https://corretto.aws/downloads/resources/17.0.6.10.1/amazon-corretto-17.0.6.10.1-alpine-linux-aarch64.tar.gz" rel="nofollow">amazon-corretto-17.0.6.10.1-alpine-linux-aarch64.tar.gz</a></td>\n<td><code>82ddc39899d0b39ea4e452add5194108</code> /<br /> <code>4211f9e47ef23995dcff2b5f0193bad68837aaae20cf85756480cc9cf6cec127</code></td>\n<td><a href="https://corretto.aws/downloads/resources/17.0.6.10.1/amazon-corretto-17.0.6.10.1-alpine-linux-aarch64.tar.gz.sig" rel="nofollow">Download</a></td>\n</tr>\n</tbody>\n</table>'}
], 
'summary': '<p>For release notes see : <a href="https://github.com/corretto/corretto-17/blob/release-17.0.6.10.1/CHANGELOG.md">CHANGELOG.md</a></p>\n<table>\n<thead>\n<tr>\n<th>Platform</th>\n<th>Type</th>\n<th>Download Link</th>\n<th>Checksum (MD5) / Checksum (SHA256)</th>\n<th>Sig File</th>\n</tr>\n</thead>\n<tbody>\n<tr>\n<td><a href="https://docs.aws.amazon.com/corretto/latest/corretto-17-ug/generic-linux-install.html" rel="nofollow">Linux x64</a></td>\n<td>JDK</td>\n<td><a href="https://corretto.aws/downloads/resources/17.0.6.10.1/java-17-amazon-corretto-jdk_17.0.6.10-1_amd64.deb" rel="nofollow">java-17-amazon-corretto-jdk_17.0.6.10-1_amd64.deb</a></td>\n<td><code>025505ee141db2a78670e2c51e1f3b5a</code> /<br /> <code>501e9f58ed19f966b4ed95623755e96c91a275244be4fca21afff2bfeaba7d14</code></td>\n<td></td>\n</tr>\n<tr>\n<td><a href="https://docs.aws.amazon.com/corretto/latest/corretto-17-ug/generic-linux-install.html" rel="nofollow">Linux x64</a></td>\n<td>JDK</td>\n<td><a href="https://corretto.aws/downloads/resources/17.0.6.10.1/java-17-amazon-corretto-devel-17.0.6.10-1.x86_64.rpm" rel="nofollow">java-17-amazon-corretto-devel-17.0.6.10-1.x86_64.rpm</a></td>\n<td><code>dd1bf75f6aa3360d312890996a5071c1</code> /<br /> <code>bcb76d3bd1f3d61c8047f929ee93b47da87f21afd4a2dee2158c09f183492e74</code></td>\n<td></td>\n</tr>\n<tr>\n<td><a href="https://docs.aws.amazon.com/corretto/latest/corretto-17-ug/generic-linux-install.html" rel="nofollow">Linux x64</a></td>\n<td>JDK</td>\n<td><a href="https://corretto.aws/downloads/resources/17.0.6.10.1/amazon-corretto-17.0.6.10.1-linux-x64.tar.gz" rel="nofollow">amazon-corretto-17.0.6.10.1-linux-x64.tar.gz</a></td>\n<td><code>50c8e341384a04b95cd1c8b698116dab</code> /<br /> <code>365bb4ae3f56bfb3c0df5f8f5b809ff0212366c46970c4b371acb80ecf4706cc</code></td>\n<td><a href="https://corretto.aws/downloads/resources/17.0.6.10.1/amazon-corretto-17.0.6.10.1-linux-x64.tar.gz.sig" rel="nofollow">Download</a></td>\n</tr>\n<tr>\n<td><a href="https://docs.aws.amazon.com/corretto/latest/corretto-17-ug/generic-linux-install.html" rel="nofollow">Linux aarch64</a></td>\n<td>JDK</td>\n<td><a href="https://corretto.aws/downloads/resources/17.0.6.10.1/java-17-amazon-corretto-jdk_17.0.6.10-1_arm64.deb" rel="nofollow">java-17-amazon-corretto-jdk_17.0.6.10-1_arm64.deb</a></td>\n<td><code>75acc3e7f135ad2d00d38a8732aa1b00</code> /<br /> <code>482f561086b4c360c33f246c87c95aeea9fbd0fdc1b540d4e504868afb262d5f</code></td>\n<td></td>\n</tr>\n<tr>\n<td><a href="https://docs.aws.amazon.com/corretto/latest/corretto-17-ug/generic-linux-install.html" rel="nofollow">Linux aarch64</a></td>\n<td>JDK</td>\n<td><a href="https://corretto.aws/downloads/resources/17.0.6.10.1/java-17-amazon-corretto-devel-17.0.6.10-1.aarch64.rpm" rel="nofollow">java-17-amazon-corretto-devel-17.0.6.10-1.aarch64.rpm</a></td>\n<td><code>4a69d896c403a1a3807627fb28dec76f</code> /<br /> <code>069ac8b950a91c24369703d67cf1e900097383ba1f053ac05a31bc6676ae9c35</code></td>\n<td></td>\n</tr>\n<tr>\n<td><a href="https://docs.aws.amazon.com/corretto/latest/corretto-17-ug/generic-linux-install.html" rel="nofollow">Linux aarch64</a></td>\n<td>JDK</td>\n<td><a href="https://corretto.aws/downloads/resources/17.0.6.10.1/amazon-corretto-17.0.6.10.1-linux-aarch64.tar.gz" rel="nofollow">amazon-corretto-17.0.6.10.1-linux-aarch64.tar.gz</a></td>\n<td><code>25be86e6a0b3cd7c56624e87cb0692d4</code> /<br /> <code>8fc36009858cfb4dbd30ba4847c6fc4d53d4f843b08dea8189f38fbf8bf40ca8</code></td>\n<td><a href="https://corretto.aws/downloads/resources/17.0.6.10.1/amazon-corretto-17.0.6.10.1-linux-aarch64.tar.gz.sig" rel="nofollow">Download</a></td>\n</tr>\n<tr>\n<td><a href="https://docs.aws.amazon.com/corretto/latest/corretto-17-ug/windows-7-install.html" rel="nofollow">Windows x64</a></td>\n<td>JDK</td>\n<td><a href="https://corretto.aws/downloads/resources/17.0.6.10.1/amazon-corretto-17.0.6.10.1-windows-x64.msi" rel="nofollow">amazon-corretto-17.0.6.10.1-windows-x64.msi</a></td>\n<td><code>1ae096ae7e62bdd28bf0e360e31ccff8</code> /<br /> <code>a2ac2df53ae6b7d0a155cdd29897701671a028a74e7f48f7e4489610589eac29</code></td>\n<td></td>\n</tr>\n<tr>\n<td><a href="https://docs.aws.amazon.com/corretto/latest/corretto-17-ug/windows-7-install.html" rel="nofollow">Windows x64</a></td>\n<td>JDK</td>\n<td><a href="https://corretto.aws/downloads/resources/17.0.6.10.1/amazon-corretto-17.0.6.10.1-windows-x64-jdk.zip" rel="nofollow">amazon-corretto-17.0.6.10.1-windows-x64-jdk.zip</a></td>\n<td><code>478628efdf21bba10b1f909cefb9e413</code> /<br /> <code>27dfa7189763bf5bee6250baef22bb6f6032deebe0edd11f79495781cc7955fe</code></td>\n<td><a href="https://corretto.aws/downloads/resources/17.0.6.10.1/amazon-corretto-17.0.6.10.1-windows-x64-jdk.zip.sig" rel="nofollow">Download</a></td>\n</tr>\n<tr>\n<td><a href="https://docs.aws.amazon.com/corretto/latest/corretto-17-ug/macos-install.html" rel="nofollow">macOS x64</a></td>\n<td>JDK</td>\n<td><a href="https://corretto.aws/downloads/resources/17.0.6.10.1/amazon-corretto-17.0.6.10.1-macosx-x64.pkg" rel="nofollow">amazon-corretto-17.0.6.10.1-macosx-x64.pkg</a></td>\n<td><code>4d6a3d571c4f718f7e268fa27bf7252e</code> /<br /> <code>4de291b2c5e4535fce01a8ced0416424352d2d320794087f62c3a6fd42a3ab0f</code></td>\n<td></td>\n</tr>\n<tr>\n<td><a href="https://docs.aws.amazon.com/corretto/latest/corretto-17-ug/macos-install.html" rel="nofollow">macOS x64</a></td>\n<td>JDK</td>\n<td><a href="https://corretto.aws/downloads/resources/17.0.6.10.1/amazon-corretto-17.0.6.10.1-macosx-x64.tar.gz" rel="nofollow">amazon-corretto-17.0.6.10.1-macosx-x64.tar.gz</a></td>\n<td><code>fe0f0a346c7108f4b70e01bdbd27317c</code> /<br /> <code>1ba7e50d74c2f402431d365eb8e5f7b860b03b18956af59f5f364f6567a8463e</code></td>\n<td><a href="https://corretto.aws/downloads/resources/17.0.6.10.1/amazon-corretto-17.0.6.10.1-macosx-x64.tar.gz.sig" rel="nofollow">Download</a></td>\n</tr>\n<tr>\n<td><a href="https://docs.aws.amazon.com/corretto/latest/corretto-17-ug/macos-install.html" rel="nofollow">macOS aarch64</a></td>\n<td>JDK</td>\n<td><a href="https://corretto.aws/downloads/resources/17.0.6.10.1/amazon-corretto-17.0.6.10.1-macosx-aarch64.pkg" rel="nofollow">amazon-corretto-17.0.6.10.1-macosx-aarch64.pkg</a></td>\n<td><code>28e1c13fe099fd28dc22963b36a18bd5</code> /<br /> <code>526d2f664bc5d93aeff6b5d8e1b45d9d644d09b1939bcabbe04cdf692c1f2db2</code></td>\n<td></td>\n</tr>\n<tr>\n<td><a href="https://docs.aws.amazon.com/corretto/latest/corretto-17-ug/macos-install.html" rel="nofollow">macOS aarch64</a></td>\n<td>JDK</td>\n<td><a href="https://corretto.aws/downloads/resources/17.0.6.10.1/amazon-corretto-17.0.6.10.1-macosx-aarch64.tar.gz" rel="nofollow">amazon-corretto-17.0.6.10.1-macosx-aarch64.tar.gz</a></td>\n<td><code>7a0a13d88cb3d4d3901332be8a87d64a</code> /<br /> <code>f7411c1d8a94681e669b133ab57a7ef815aa145b3ecc041c93ca7ff1eb1811b3</code></td>\n<td><a href="https://corretto.aws/downloads/resources/17.0.6.10.1/amazon-corretto-17.0.6.10.1-macosx-aarch64.tar.gz.sig" rel="nofollow">Download</a></td>\n</tr>\n<tr>\n<td><a href="https://docs.aws.amazon.com/corretto/latest/corretto-17-ug/generic-linux-install.html" rel="nofollow">Alpine Linux x64</a></td>\n<td>JDK</td>\n<td><a href="https://corretto.aws/downloads/resources/17.0.6.10.1/amazon-corretto-17.0.6.10.1-alpine-linux-x64.tar.gz" rel="nofollow">amazon-corretto-17.0.6.10.1-alpine-linux-x64.tar.gz</a></td>\n<td><code>952ddd95dfa688f4bea15a87a0137f9e</code> /<br /> <code>49d2131a3fd23c13c429d4c666719e9859be9a389fec20605ce4ee706a7c6640</code></td>\n<td><a href="https://corretto.aws/downloads/resources/17.0.6.10.1/amazon-corretto-17.0.6.10.1-alpine-linux-x64.tar.gz.sig" rel="nofollow">Download</a></td>\n</tr>\n<tr>\n<td><a href="https://docs.aws.amazon.com/corretto/latest/corretto-17-ug/generic-linux-install.html" rel="nofollow">Alpine Linux aarch64</a> (preview)</td>\n<td>JDK</td>\n<td><a href="https://corretto.aws/downloads/resources/17.0.6.10.1/amazon-corretto-17.0.6.10.1-alpine-linux-aarch64.tar.gz" rel="nofollow">amazon-corretto-17.0.6.10.1-alpine-linux-aarch64.tar.gz</a></td>\n<td><code>82ddc39899d0b39ea4e452add5194108</code> /<br /> <code>4211f9e47ef23995dcff2b5f0193bad68837aaae20cf85756480cc9cf6cec127</code></td>\n<td><a href="https://corretto.aws/downloads/resources/17.0.6.10.1/amazon-corretto-17.0.6.10.1-alpine-linux-aarch64.tar.gz.sig" rel="nofollow">Download</a></td>\n</tr>\n</tbody>\n</table>', 
'authors': [{'name': 'Rudometov'}], 
'author_detail': {'name': 'Rudometov'}, 
'author': 'Rudometov', 
'media_thumbnail': [
		{'height': '30', 'width': '30', 'url': 'https://avatars.githubusercontent.com/u/2694233?s=60&v=4'}
], 
'href': ''
}
```

## Maven Feed

URL

```bash
https://github.com/apache/maven/releases.atom
```

Key components

```bash
'title': '3.9.0', 
'updated': '2023-02-14T17:38:12Z', 
'link': 'https://github.com/apache/maven/releases/tag/maven-3.9.0', 
'summary': '<p><a href="https://maven.apache.org/docs/3.9.0/release-notes.html" rel="nofollow">Release Notes - Maven - Version 3.9.0</a></p>\n<h2>Sub-task</h2>\n<ul>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7019" rel="nofollow">MNG-7019</a>] - Notify also at start when profile is missing</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7447" rel="nofollow">MNG-7447</a>] - Several Improvements by using Stream API</li>\n</ul>\n<h2>Bug</h2>\n<ul>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-5222" rel="nofollow">MNG-5222</a>] - Maven 3 no longer logs warnings about deprecated plugin parameters.</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-6965" rel="nofollow">MNG-6965</a>] - Extensions suddenly have org.codehaus.plexus:plexus-utils:jar:1.1 on their classpath</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7055" rel="nofollow">MNG-7055</a>] - Using MINSTALL/DEPLOY 3.0.0-M1+ does not write plugin information into maven-metadata.xml</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7106" rel="nofollow">MNG-7106</a>] - VersionRange.toString() produces a string that cannot be parsed with VersionRange.createFromVersionSpec() for same lower and upper bounds</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7131" rel="nofollow">MNG-7131</a>] - maven.config doesn\'t handle arguments with spaces in them</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7160" rel="nofollow">MNG-7160</a>] - Extension And Classloaders: difference of result given extension types</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7316" rel="nofollow">MNG-7316</a>] - REGRESSION: MavenProject.getAttachedArtifacts() is read-only</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7352" rel="nofollow">MNG-7352</a>] - org.apache.maven.toolchain.java.JavaToolchainImpl should be public</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7413" rel="nofollow">MNG-7413</a>] - Fix POM model documentation confusion on report plugins, distribution repository and profile build</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7425" rel="nofollow">MNG-7425</a>] - Maven artifact downloads sometimes result in empty zip files in local repository</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7432" rel="nofollow">MNG-7432</a>] - [REGRESSION] Resolver session contains non-MavenWorkspaceReader</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7433" rel="nofollow">MNG-7433</a>] - [REGRESSION] Multiple maven instances working on same source tree can lock each other</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7441" rel="nofollow">MNG-7441</a>] - Update Version of (optional) Logback to Address <a href="https://github.com/advisories/GHSA-668q-qrv7-99fm" title="CVE-2021-42550">CVE-2021-42550</a></li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7448" rel="nofollow">MNG-7448</a>] - Don\'t ignore bin/ otherwise bin/ in apache-maven module cannot be readded</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7459" rel="nofollow">MNG-7459</a>] - Revert <a class="issue-link js-issue-link notranslate" href="https://issues.apache.org/jira/browse/MNG-7347" rel="noopener noreferrer nofollow">MNG-7347</a> (SessionScoped beans should be singletons for a given session)</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7471" rel="nofollow">MNG-7471</a>] - Resolver 1.8.0 introduces binary breakage in plugin using Resolver</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7487" rel="nofollow">MNG-7487</a>] - Fix deadlock during forked lifecycle executions</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7493" rel="nofollow">MNG-7493</a>] - [REGRESSION] Resolving dependencies between submodules fails</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7504" rel="nofollow">MNG-7504</a>] - Warning about unknown reportPlugins parameters for m-site-p are always generated</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7511" rel="nofollow">MNG-7511</a>] - Ensure the degreeOfConcurrency is a positive number in MavenExecutionRequest</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7515" rel="nofollow">MNG-7515</a>] - Cannot see a dependency tree for apache-maven module</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7529" rel="nofollow">MNG-7529</a>] - Maven resolver makes bad repository choices when resolving version ranges</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7545" rel="nofollow">MNG-7545</a>] - Multi building can create bad files for downloaded artifacts in local repository</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7563" rel="nofollow">MNG-7563</a>] - REGRESSION: User properties now override model properties in dependencies</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7564" rel="nofollow">MNG-7564</a>] - Potential NPE in MavenMetadataSource</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7568" rel="nofollow">MNG-7568</a>] - [WARNING] The requested profile "ABCDEF" could not be activated because it does not exist.</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7578" rel="nofollow">MNG-7578</a>] - Building Linux image on Windows impossible (patch incuded)</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7600" rel="nofollow">MNG-7600</a>] - LocalRepositoryManager is created too early</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7606" rel="nofollow">MNG-7606</a>] - Maven 3.9.0-SNAPSHOT cannot build Maven 4.0.0-SNAPSHOT</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7621" rel="nofollow">MNG-7621</a>] - Parameter \'-f\' causes ignoring any \'maven.config\' (only on Windows)</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7624" rel="nofollow">MNG-7624</a>] - Plugins without non-mandatory goalPrefix are now logging incomplete info</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7637" rel="nofollow">MNG-7637</a>] - Possible NPE in MavenProject#hashCode()</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7644" rel="nofollow">MNG-7644</a>] - Fix version comparison where .X1 &lt; -X2 for any string qualifier X</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7648" rel="nofollow">MNG-7648</a>] - Generated model reader is not setting location information</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7672" rel="nofollow">MNG-7672</a>] - Aggregate goals executed in a submodule forks the whole reactor</li>\n</ul>\n<h2>New Feature</h2>\n<ul>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-3655" rel="nofollow">MNG-3655</a>] - Allow multiple local repositories</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-6270" rel="nofollow">MNG-6270</a>] - Store snapshots in a separate local repository</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7193" rel="nofollow">MNG-7193</a>] - Introduce MAVEN_ARGS environment variable</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7353" rel="nofollow">MNG-7353</a>] - Add support for "mvn pluginPrefix:version:goal"</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7391" rel="nofollow">MNG-7391</a>] - Add MojoExecution strategy and runner required by Maven Build Cache Extension</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7454" rel="nofollow">MNG-7454</a>] - Include resolver-transport-http in Maven</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7457" rel="nofollow">MNG-7457</a>] - Warn about deprecated plugin Mojo</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7464" rel="nofollow">MNG-7464</a>] - Warn about using read-only parameters for Mojo in configuration</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7468" rel="nofollow">MNG-7468</a>] - Unsupported plugins parameters in configuration should be verified</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7486" rel="nofollow">MNG-7486</a>] - Create a multiline message helper for boxed log messages</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7612" rel="nofollow">MNG-7612</a>] - Chained Local Repository</li>\n</ul>\n<h2>Improvement</h2>\n<ul>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-6609" rel="nofollow">MNG-6609</a>] - Profile activation by packaging</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-6826" rel="nofollow">MNG-6826</a>] - Remove condition check for JDK8+ in FileSizeFormatTest</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-6972" rel="nofollow">MNG-6972</a>] - Allow access to org.apache.maven.graph</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7068" rel="nofollow">MNG-7068</a>] - Active dependency management for Google Guice/Guava</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7350" rel="nofollow">MNG-7350</a>] - Introduce a factory for ModelCache</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7401" rel="nofollow">MNG-7401</a>] - Make MavenSession#getCurrentProject() using a thread local</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7438" rel="nofollow">MNG-7438</a>] - add execution id to "Configuring mojo xxx with basic configurator" debug message</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7445" rel="nofollow">MNG-7445</a>] - to refactor some useless code</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7463" rel="nofollow">MNG-7463</a>] - Improve documentation about deprecation in Mojo</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7474" rel="nofollow">MNG-7474</a>] - SessionScoped beans should be singletons for a given session</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7476" rel="nofollow">MNG-7476</a>] - Display a warning when an aggregator mojo is locking other mojo executions</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7478" rel="nofollow">MNG-7478</a>] - Improve transport selection for resolver</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7501" rel="nofollow">MNG-7501</a>] - display relative path to pom.xml</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7520" rel="nofollow">MNG-7520</a>] - Simplify integration of Redisson and Hazelcast for Maven Resolver</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7547" rel="nofollow">MNG-7547</a>] - Simplify G level metadata handling</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7561" rel="nofollow">MNG-7561</a>] - DefaultVersionRangeResolver should not try to resolve versions with same upper and lower bound</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7590" rel="nofollow">MNG-7590</a>] - Allow configure resolver by properties in settings.xml</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7608" rel="nofollow">MNG-7608</a>] - Make Resolver native transport the default in Maven</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7614" rel="nofollow">MNG-7614</a>] - Maven should translate transport configuration fully to resolver transports.</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7619" rel="nofollow">MNG-7619</a>] - Maven should explain why an artifact is present in local repository</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7645" rel="nofollow">MNG-7645</a>] - Implement some #toString() methods</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7651" rel="nofollow">MNG-7651</a>] - Simplify and document merge of maven.config file and CLI args</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7658" rel="nofollow">MNG-7658</a>] - CI-friendly versions should only come from/rely on user properties</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7666" rel="nofollow">MNG-7666</a>] - Update default binding and lifecycle plugin versions</li>\n</ul>\n<h2>Task</h2>\n<ul>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-6399" rel="nofollow">MNG-6399</a>] - Lift JDK minimum to JDK 8</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7452" rel="nofollow">MNG-7452</a>] - Remove JDK7 run on Maven 3.9.X Branch</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7466" rel="nofollow">MNG-7466</a>] - Align Assembly Descriptor NS versions</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7513" rel="nofollow">MNG-7513</a>] - Address commons-io_commons-io vulnerability found in maven latest version</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7523" rel="nofollow">MNG-7523</a>] - Back port MAVEN_ARGS to Apache Maven 3.9.0</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7556" rel="nofollow">MNG-7556</a>] - Clean up notion between user properties and system properties</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7618" rel="nofollow">MNG-7618</a>] - Use goalPrefix instead of artifactId to display mojos being executed</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7634" rel="nofollow">MNG-7634</a>] - Revert <a class="issue-link js-issue-link notranslate" href="https://issues.apache.org/jira/browse/MNG-5982" rel="noopener noreferrer nofollow">MNG-5982</a> and <a class="issue-link js-issue-link notranslate" href="https://issues.apache.org/jira/browse/MNG-7417" rel="noopener noreferrer nofollow">MNG-7417</a></li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7636" rel="nofollow">MNG-7636</a>] - Partially revert <a class="issue-link js-issue-link notranslate" href="https://issues.apache.org/jira/browse/MNG-5868" rel="noopener noreferrer nofollow">MNG-5868</a> to restore backward compatibility (see <a class="issue-link js-issue-link notranslate" href="https://issues.apache.org/jira/browse/MNG-7316" rel="noopener noreferrer nofollow">MNG-7316</a>)</li>\n</ul>\n<h2>Dependency upgrade</h2>\n<ul>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-6878" rel="nofollow">MNG-6878</a>] - Upgrade Guice to 4.2.3</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7247" rel="nofollow">MNG-7247</a>] - Upgrade Maven Resolver to 1.7.2</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7453" rel="nofollow">MNG-7453</a>] - Upgrade Maven Resolver to 1.8.0</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7488" rel="nofollow">MNG-7488</a>] - Upgrade SLF4J to 1.7.36</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7489" rel="nofollow">MNG-7489</a>] - Upgrade JUnit to 4.13.2</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7491" rel="nofollow">MNG-7491</a>] - Update parent POM to 36</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7499" rel="nofollow">MNG-7499</a>] - Upgrade Maven Resolver to 1.8.1</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7502" rel="nofollow">MNG-7502</a>] - Upgrade Guice to 5.1.0</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7506" rel="nofollow">MNG-7506</a>] - Upgrade Maven Wagon to 3.5.2</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7522" rel="nofollow">MNG-7522</a>] - Upgrade Maven Resolver to 1.8.2</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7530" rel="nofollow">MNG-7530</a>] - Upgrade Apache Maven parent POM to version 37</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7586" rel="nofollow">MNG-7586</a>] - Update Maven Resolver to 1.9.2</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7613" rel="nofollow">MNG-7613</a>] - Upgrade Apache Maven parent POM to version 38</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7641" rel="nofollow">MNG-7641</a>] - Upgrade Maven Wagon to 3.5.3</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7668" rel="nofollow">MNG-7668</a>] - Update Maven Resolver to 1.9.4</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7675" rel="nofollow">MNG-7675</a>] - Update Maven Parent to 39</li>\n</ul>',
```

Constraint

- Cannot filter pre-releases as there is no identifier within entry to distinguish release types
    - Requires Gitlab API

raw sample rss entry

```bash
{
'id': 'tag:github.com,2008:Repository/206483/maven-3.9.0', 
'guidislink': True, 
'link': 'https://github.com/apache/maven/releases/tag/maven-3.9.0', 
'updated': '2023-02-14T17:38:12Z', 
'updated_parsed': 
		time.struct_time(
				tm_year=2023, 
				tm_mon=2, 
				tm_mday=14, 
				tm_hour=17, 
				tm_min=38, 
				tm_sec=12, 
				tm_wday=1, 
				tm_yday=45, 
				tm_isdst=0), 
'links': [
		{'rel': 'alternate', 'type': 'text/html', 
			'href': 'https://github.com/apache/maven/releases/tag/maven-3.9.0'}
], 
'title': '3.9.0', 
'title_detail': 
		{'type': 'text/plain', 
			'language': 'en-US', 
			'base': 'https://github.com/apache/maven/releases.atom', 
			'value': '3.9.0'}, 
'content': [
		{'type': 'text/html', 'language': 'en-US', 
			'base': 'https://github.com/apache/maven/releases.atom', 
			'value': '<p><a href="https://maven.apache.org/docs/3.9.0/release-notes.html" rel="nofollow">Release Notes - Maven - Version 3.9.0</a></p>\n<h2>Sub-task</h2>\n<ul>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7019" rel="nofollow">MNG-7019</a>] - Notify also at start when profile is missing</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7447" rel="nofollow">MNG-7447</a>] - Several Improvements by using Stream API</li>\n</ul>\n<h2>Bug</h2>\n<ul>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-5222" rel="nofollow">MNG-5222</a>] - Maven 3 no longer logs warnings about deprecated plugin parameters.</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-6965" rel="nofollow">MNG-6965</a>] - Extensions suddenly have org.codehaus.plexus:plexus-utils:jar:1.1 on their classpath</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7055" rel="nofollow">MNG-7055</a>] - Using MINSTALL/DEPLOY 3.0.0-M1+ does not write plugin information into maven-metadata.xml</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7106" rel="nofollow">MNG-7106</a>] - VersionRange.toString() produces a string that cannot be parsed with VersionRange.createFromVersionSpec() for same lower and upper bounds</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7131" rel="nofollow">MNG-7131</a>] - maven.config doesn\'t handle arguments with spaces in them</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7160" rel="nofollow">MNG-7160</a>] - Extension And Classloaders: difference of result given extension types</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7316" rel="nofollow">MNG-7316</a>] - REGRESSION: MavenProject.getAttachedArtifacts() is read-only</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7352" rel="nofollow">MNG-7352</a>] - org.apache.maven.toolchain.java.JavaToolchainImpl should be public</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7413" rel="nofollow">MNG-7413</a>] - Fix POM model documentation confusion on report plugins, distribution repository and profile build</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7425" rel="nofollow">MNG-7425</a>] - Maven artifact downloads sometimes result in empty zip files in local repository</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7432" rel="nofollow">MNG-7432</a>] - [REGRESSION] Resolver session contains non-MavenWorkspaceReader</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7433" rel="nofollow">MNG-7433</a>] - [REGRESSION] Multiple maven instances working on same source tree can lock each other</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7441" rel="nofollow">MNG-7441</a>] - Update Version of (optional) Logback to Address <a href="https://github.com/advisories/GHSA-668q-qrv7-99fm" title="CVE-2021-42550">CVE-2021-42550</a></li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7448" rel="nofollow">MNG-7448</a>] - Don\'t ignore bin/ otherwise bin/ in apache-maven module cannot be readded</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7459" rel="nofollow">MNG-7459</a>] - Revert <a class="issue-link js-issue-link notranslate" href="https://issues.apache.org/jira/browse/MNG-7347" rel="noopener noreferrer nofollow">MNG-7347</a> (SessionScoped beans should be singletons for a given session)</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7471" rel="nofollow">MNG-7471</a>] - Resolver 1.8.0 introduces binary breakage in plugin using Resolver</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7487" rel="nofollow">MNG-7487</a>] - Fix deadlock during forked lifecycle executions</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7493" rel="nofollow">MNG-7493</a>] - [REGRESSION] Resolving dependencies between submodules fails</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7504" rel="nofollow">MNG-7504</a>] - Warning about unknown reportPlugins parameters for m-site-p are always generated</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7511" rel="nofollow">MNG-7511</a>] - Ensure the degreeOfConcurrency is a positive number in MavenExecutionRequest</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7515" rel="nofollow">MNG-7515</a>] - Cannot see a dependency tree for apache-maven module</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7529" rel="nofollow">MNG-7529</a>] - Maven resolver makes bad repository choices when resolving version ranges</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7545" rel="nofollow">MNG-7545</a>] - Multi building can create bad files for downloaded artifacts in local repository</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7563" rel="nofollow">MNG-7563</a>] - REGRESSION: User properties now override model properties in dependencies</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7564" rel="nofollow">MNG-7564</a>] - Potential NPE in MavenMetadataSource</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7568" rel="nofollow">MNG-7568</a>] - [WARNING] The requested profile "ABCDEF" could not be activated because it does not exist.</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7578" rel="nofollow">MNG-7578</a>] - Building Linux image on Windows impossible (patch incuded)</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7600" rel="nofollow">MNG-7600</a>] - LocalRepositoryManager is created too early</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7606" rel="nofollow">MNG-7606</a>] - Maven 3.9.0-SNAPSHOT cannot build Maven 4.0.0-SNAPSHOT</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7621" rel="nofollow">MNG-7621</a>] - Parameter \'-f\' causes ignoring any \'maven.config\' (only on Windows)</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7624" rel="nofollow">MNG-7624</a>] - Plugins without non-mandatory goalPrefix are now logging incomplete info</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7637" rel="nofollow">MNG-7637</a>] - Possible NPE in MavenProject#hashCode()</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7644" rel="nofollow">MNG-7644</a>] - Fix version comparison where .X1 &lt; -X2 for any string qualifier X</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7648" rel="nofollow">MNG-7648</a>] - Generated model reader is not setting location information</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7672" rel="nofollow">MNG-7672</a>] - Aggregate goals executed in a submodule forks the whole reactor</li>\n</ul>\n<h2>New Feature</h2>\n<ul>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-3655" rel="nofollow">MNG-3655</a>] - Allow multiple local repositories</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-6270" rel="nofollow">MNG-6270</a>] - Store snapshots in a separate local repository</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7193" rel="nofollow">MNG-7193</a>] - Introduce MAVEN_ARGS environment variable</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7353" rel="nofollow">MNG-7353</a>] - Add support for "mvn pluginPrefix:version:goal"</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7391" rel="nofollow">MNG-7391</a>] - Add MojoExecution strategy and runner required by Maven Build Cache Extension</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7454" rel="nofollow">MNG-7454</a>] - Include resolver-transport-http in Maven</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7457" rel="nofollow">MNG-7457</a>] - Warn about deprecated plugin Mojo</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7464" rel="nofollow">MNG-7464</a>] - Warn about using read-only parameters for Mojo in configuration</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7468" rel="nofollow">MNG-7468</a>] - Unsupported plugins parameters in configuration should be verified</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7486" rel="nofollow">MNG-7486</a>] - Create a multiline message helper for boxed log messages</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7612" rel="nofollow">MNG-7612</a>] - Chained Local Repository</li>\n</ul>\n<h2>Improvement</h2>\n<ul>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-6609" rel="nofollow">MNG-6609</a>] - Profile activation by packaging</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-6826" rel="nofollow">MNG-6826</a>] - Remove condition check for JDK8+ in FileSizeFormatTest</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-6972" rel="nofollow">MNG-6972</a>] - Allow access to org.apache.maven.graph</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7068" rel="nofollow">MNG-7068</a>] - Active dependency management for Google Guice/Guava</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7350" rel="nofollow">MNG-7350</a>] - Introduce a factory for ModelCache</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7401" rel="nofollow">MNG-7401</a>] - Make MavenSession#getCurrentProject() using a thread local</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7438" rel="nofollow">MNG-7438</a>] - add execution id to "Configuring mojo xxx with basic configurator" debug message</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7445" rel="nofollow">MNG-7445</a>] - to refactor some useless code</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7463" rel="nofollow">MNG-7463</a>] - Improve documentation about deprecation in Mojo</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7474" rel="nofollow">MNG-7474</a>] - SessionScoped beans should be singletons for a given session</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7476" rel="nofollow">MNG-7476</a>] - Display a warning when an aggregator mojo is locking other mojo executions</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7478" rel="nofollow">MNG-7478</a>] - Improve transport selection for resolver</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7501" rel="nofollow">MNG-7501</a>] - display relative path to pom.xml</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7520" rel="nofollow">MNG-7520</a>] - Simplify integration of Redisson and Hazelcast for Maven Resolver</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7547" rel="nofollow">MNG-7547</a>] - Simplify G level metadata handling</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7561" rel="nofollow">MNG-7561</a>] - DefaultVersionRangeResolver should not try to resolve versions with same upper and lower bound</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7590" rel="nofollow">MNG-7590</a>] - Allow configure resolver by properties in settings.xml</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7608" rel="nofollow">MNG-7608</a>] - Make Resolver native transport the default in Maven</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7614" rel="nofollow">MNG-7614</a>] - Maven should translate transport configuration fully to resolver transports.</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7619" rel="nofollow">MNG-7619</a>] - Maven should explain why an artifact is present in local repository</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7645" rel="nofollow">MNG-7645</a>] - Implement some #toString() methods</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7651" rel="nofollow">MNG-7651</a>] - Simplify and document merge of maven.config file and CLI args</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7658" rel="nofollow">MNG-7658</a>] - CI-friendly versions should only come from/rely on user properties</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7666" rel="nofollow">MNG-7666</a>] - Update default binding and lifecycle plugin versions</li>\n</ul>\n<h2>Task</h2>\n<ul>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-6399" rel="nofollow">MNG-6399</a>] - Lift JDK minimum to JDK 8</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7452" rel="nofollow">MNG-7452</a>] - Remove JDK7 run on Maven 3.9.X Branch</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7466" rel="nofollow">MNG-7466</a>] - Align Assembly Descriptor NS versions</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7513" rel="nofollow">MNG-7513</a>] - Address commons-io_commons-io vulnerability found in maven latest version</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7523" rel="nofollow">MNG-7523</a>] - Back port MAVEN_ARGS to Apache Maven 3.9.0</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7556" rel="nofollow">MNG-7556</a>] - Clean up notion between user properties and system properties</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7618" rel="nofollow">MNG-7618</a>] - Use goalPrefix instead of artifactId to display mojos being executed</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7634" rel="nofollow">MNG-7634</a>] - Revert <a class="issue-link js-issue-link notranslate" href="https://issues.apache.org/jira/browse/MNG-5982" rel="noopener noreferrer nofollow">MNG-5982</a> and <a class="issue-link js-issue-link notranslate" href="https://issues.apache.org/jira/browse/MNG-7417" rel="noopener noreferrer nofollow">MNG-7417</a></li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7636" rel="nofollow">MNG-7636</a>] - Partially revert <a class="issue-link js-issue-link notranslate" href="https://issues.apache.org/jira/browse/MNG-5868" rel="noopener noreferrer nofollow">MNG-5868</a> to restore backward compatibility (see <a class="issue-link js-issue-link notranslate" href="https://issues.apache.org/jira/browse/MNG-7316" rel="noopener noreferrer nofollow">MNG-7316</a>)</li>\n</ul>\n<h2>Dependency upgrade</h2>\n<ul>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-6878" rel="nofollow">MNG-6878</a>] - Upgrade Guice to 4.2.3</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7247" rel="nofollow">MNG-7247</a>] - Upgrade Maven Resolver to 1.7.2</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7453" rel="nofollow">MNG-7453</a>] - Upgrade Maven Resolver to 1.8.0</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7488" rel="nofollow">MNG-7488</a>] - Upgrade SLF4J to 1.7.36</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7489" rel="nofollow">MNG-7489</a>] - Upgrade JUnit to 4.13.2</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7491" rel="nofollow">MNG-7491</a>] - Update parent POM to 36</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7499" rel="nofollow">MNG-7499</a>] - Upgrade Maven Resolver to 1.8.1</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7502" rel="nofollow">MNG-7502</a>] - Upgrade Guice to 5.1.0</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7506" rel="nofollow">MNG-7506</a>] - Upgrade Maven Wagon to 3.5.2</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7522" rel="nofollow">MNG-7522</a>] - Upgrade Maven Resolver to 1.8.2</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7530" rel="nofollow">MNG-7530</a>] - Upgrade Apache Maven parent POM to version 37</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7586" rel="nofollow">MNG-7586</a>] - Update Maven Resolver to 1.9.2</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7613" rel="nofollow">MNG-7613</a>] - Upgrade Apache Maven parent POM to version 38</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7641" rel="nofollow">MNG-7641</a>] - Upgrade Maven Wagon to 3.5.3</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7668" rel="nofollow">MNG-7668</a>] - Update Maven Resolver to 1.9.4</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7675" rel="nofollow">MNG-7675</a>] - Update Maven Parent to 39</li>\n</ul>'}], 
'summary': '<p><a href="https://maven.apache.org/docs/3.9.0/release-notes.html" rel="nofollow">Release Notes - Maven - Version 3.9.0</a></p>\n<h2>Sub-task</h2>\n<ul>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7019" rel="nofollow">MNG-7019</a>] - Notify also at start when profile is missing</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7447" rel="nofollow">MNG-7447</a>] - Several Improvements by using Stream API</li>\n</ul>\n<h2>Bug</h2>\n<ul>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-5222" rel="nofollow">MNG-5222</a>] - Maven 3 no longer logs warnings about deprecated plugin parameters.</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-6965" rel="nofollow">MNG-6965</a>] - Extensions suddenly have org.codehaus.plexus:plexus-utils:jar:1.1 on their classpath</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7055" rel="nofollow">MNG-7055</a>] - Using MINSTALL/DEPLOY 3.0.0-M1+ does not write plugin information into maven-metadata.xml</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7106" rel="nofollow">MNG-7106</a>] - VersionRange.toString() produces a string that cannot be parsed with VersionRange.createFromVersionSpec() for same lower and upper bounds</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7131" rel="nofollow">MNG-7131</a>] - maven.config doesn\'t handle arguments with spaces in them</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7160" rel="nofollow">MNG-7160</a>] - Extension And Classloaders: difference of result given extension types</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7316" rel="nofollow">MNG-7316</a>] - REGRESSION: MavenProject.getAttachedArtifacts() is read-only</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7352" rel="nofollow">MNG-7352</a>] - org.apache.maven.toolchain.java.JavaToolchainImpl should be public</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7413" rel="nofollow">MNG-7413</a>] - Fix POM model documentation confusion on report plugins, distribution repository and profile build</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7425" rel="nofollow">MNG-7425</a>] - Maven artifact downloads sometimes result in empty zip files in local repository</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7432" rel="nofollow">MNG-7432</a>] - [REGRESSION] Resolver session contains non-MavenWorkspaceReader</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7433" rel="nofollow">MNG-7433</a>] - [REGRESSION] Multiple maven instances working on same source tree can lock each other</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7441" rel="nofollow">MNG-7441</a>] - Update Version of (optional) Logback to Address <a href="https://github.com/advisories/GHSA-668q-qrv7-99fm" title="CVE-2021-42550">CVE-2021-42550</a></li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7448" rel="nofollow">MNG-7448</a>] - Don\'t ignore bin/ otherwise bin/ in apache-maven module cannot be readded</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7459" rel="nofollow">MNG-7459</a>] - Revert <a class="issue-link js-issue-link notranslate" href="https://issues.apache.org/jira/browse/MNG-7347" rel="noopener noreferrer nofollow">MNG-7347</a> (SessionScoped beans should be singletons for a given session)</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7471" rel="nofollow">MNG-7471</a>] - Resolver 1.8.0 introduces binary breakage in plugin using Resolver</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7487" rel="nofollow">MNG-7487</a>] - Fix deadlock during forked lifecycle executions</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7493" rel="nofollow">MNG-7493</a>] - [REGRESSION] Resolving dependencies between submodules fails</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7504" rel="nofollow">MNG-7504</a>] - Warning about unknown reportPlugins parameters for m-site-p are always generated</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7511" rel="nofollow">MNG-7511</a>] - Ensure the degreeOfConcurrency is a positive number in MavenExecutionRequest</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7515" rel="nofollow">MNG-7515</a>] - Cannot see a dependency tree for apache-maven module</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7529" rel="nofollow">MNG-7529</a>] - Maven resolver makes bad repository choices when resolving version ranges</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7545" rel="nofollow">MNG-7545</a>] - Multi building can create bad files for downloaded artifacts in local repository</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7563" rel="nofollow">MNG-7563</a>] - REGRESSION: User properties now override model properties in dependencies</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7564" rel="nofollow">MNG-7564</a>] - Potential NPE in MavenMetadataSource</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7568" rel="nofollow">MNG-7568</a>] - [WARNING] The requested profile "ABCDEF" could not be activated because it does not exist.</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7578" rel="nofollow">MNG-7578</a>] - Building Linux image on Windows impossible (patch incuded)</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7600" rel="nofollow">MNG-7600</a>] - LocalRepositoryManager is created too early</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7606" rel="nofollow">MNG-7606</a>] - Maven 3.9.0-SNAPSHOT cannot build Maven 4.0.0-SNAPSHOT</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7621" rel="nofollow">MNG-7621</a>] - Parameter \'-f\' causes ignoring any \'maven.config\' (only on Windows)</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7624" rel="nofollow">MNG-7624</a>] - Plugins without non-mandatory goalPrefix are now logging incomplete info</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7637" rel="nofollow">MNG-7637</a>] - Possible NPE in MavenProject#hashCode()</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7644" rel="nofollow">MNG-7644</a>] - Fix version comparison where .X1 &lt; -X2 for any string qualifier X</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7648" rel="nofollow">MNG-7648</a>] - Generated model reader is not setting location information</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7672" rel="nofollow">MNG-7672</a>] - Aggregate goals executed in a submodule forks the whole reactor</li>\n</ul>\n<h2>New Feature</h2>\n<ul>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-3655" rel="nofollow">MNG-3655</a>] - Allow multiple local repositories</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-6270" rel="nofollow">MNG-6270</a>] - Store snapshots in a separate local repository</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7193" rel="nofollow">MNG-7193</a>] - Introduce MAVEN_ARGS environment variable</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7353" rel="nofollow">MNG-7353</a>] - Add support for "mvn pluginPrefix:version:goal"</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7391" rel="nofollow">MNG-7391</a>] - Add MojoExecution strategy and runner required by Maven Build Cache Extension</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7454" rel="nofollow">MNG-7454</a>] - Include resolver-transport-http in Maven</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7457" rel="nofollow">MNG-7457</a>] - Warn about deprecated plugin Mojo</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7464" rel="nofollow">MNG-7464</a>] - Warn about using read-only parameters for Mojo in configuration</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7468" rel="nofollow">MNG-7468</a>] - Unsupported plugins parameters in configuration should be verified</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7486" rel="nofollow">MNG-7486</a>] - Create a multiline message helper for boxed log messages</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7612" rel="nofollow">MNG-7612</a>] - Chained Local Repository</li>\n</ul>\n<h2>Improvement</h2>\n<ul>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-6609" rel="nofollow">MNG-6609</a>] - Profile activation by packaging</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-6826" rel="nofollow">MNG-6826</a>] - Remove condition check for JDK8+ in FileSizeFormatTest</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-6972" rel="nofollow">MNG-6972</a>] - Allow access to org.apache.maven.graph</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7068" rel="nofollow">MNG-7068</a>] - Active dependency management for Google Guice/Guava</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7350" rel="nofollow">MNG-7350</a>] - Introduce a factory for ModelCache</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7401" rel="nofollow">MNG-7401</a>] - Make MavenSession#getCurrentProject() using a thread local</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7438" rel="nofollow">MNG-7438</a>] - add execution id to "Configuring mojo xxx with basic configurator" debug message</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7445" rel="nofollow">MNG-7445</a>] - to refactor some useless code</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7463" rel="nofollow">MNG-7463</a>] - Improve documentation about deprecation in Mojo</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7474" rel="nofollow">MNG-7474</a>] - SessionScoped beans should be singletons for a given session</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7476" rel="nofollow">MNG-7476</a>] - Display a warning when an aggregator mojo is locking other mojo executions</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7478" rel="nofollow">MNG-7478</a>] - Improve transport selection for resolver</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7501" rel="nofollow">MNG-7501</a>] - display relative path to pom.xml</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7520" rel="nofollow">MNG-7520</a>] - Simplify integration of Redisson and Hazelcast for Maven Resolver</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7547" rel="nofollow">MNG-7547</a>] - Simplify G level metadata handling</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7561" rel="nofollow">MNG-7561</a>] - DefaultVersionRangeResolver should not try to resolve versions with same upper and lower bound</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7590" rel="nofollow">MNG-7590</a>] - Allow configure resolver by properties in settings.xml</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7608" rel="nofollow">MNG-7608</a>] - Make Resolver native transport the default in Maven</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7614" rel="nofollow">MNG-7614</a>] - Maven should translate transport configuration fully to resolver transports.</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7619" rel="nofollow">MNG-7619</a>] - Maven should explain why an artifact is present in local repository</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7645" rel="nofollow">MNG-7645</a>] - Implement some #toString() methods</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7651" rel="nofollow">MNG-7651</a>] - Simplify and document merge of maven.config file and CLI args</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7658" rel="nofollow">MNG-7658</a>] - CI-friendly versions should only come from/rely on user properties</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7666" rel="nofollow">MNG-7666</a>] - Update default binding and lifecycle plugin versions</li>\n</ul>\n<h2>Task</h2>\n<ul>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-6399" rel="nofollow">MNG-6399</a>] - Lift JDK minimum to JDK 8</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7452" rel="nofollow">MNG-7452</a>] - Remove JDK7 run on Maven 3.9.X Branch</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7466" rel="nofollow">MNG-7466</a>] - Align Assembly Descriptor NS versions</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7513" rel="nofollow">MNG-7513</a>] - Address commons-io_commons-io vulnerability found in maven latest version</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7523" rel="nofollow">MNG-7523</a>] - Back port MAVEN_ARGS to Apache Maven 3.9.0</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7556" rel="nofollow">MNG-7556</a>] - Clean up notion between user properties and system properties</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7618" rel="nofollow">MNG-7618</a>] - Use goalPrefix instead of artifactId to display mojos being executed</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7634" rel="nofollow">MNG-7634</a>] - Revert <a class="issue-link js-issue-link notranslate" href="https://issues.apache.org/jira/browse/MNG-5982" rel="noopener noreferrer nofollow">MNG-5982</a> and <a class="issue-link js-issue-link notranslate" href="https://issues.apache.org/jira/browse/MNG-7417" rel="noopener noreferrer nofollow">MNG-7417</a></li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7636" rel="nofollow">MNG-7636</a>] - Partially revert <a class="issue-link js-issue-link notranslate" href="https://issues.apache.org/jira/browse/MNG-5868" rel="noopener noreferrer nofollow">MNG-5868</a> to restore backward compatibility (see <a class="issue-link js-issue-link notranslate" href="https://issues.apache.org/jira/browse/MNG-7316" rel="noopener noreferrer nofollow">MNG-7316</a>)</li>\n</ul>\n<h2>Dependency upgrade</h2>\n<ul>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-6878" rel="nofollow">MNG-6878</a>] - Upgrade Guice to 4.2.3</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7247" rel="nofollow">MNG-7247</a>] - Upgrade Maven Resolver to 1.7.2</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7453" rel="nofollow">MNG-7453</a>] - Upgrade Maven Resolver to 1.8.0</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7488" rel="nofollow">MNG-7488</a>] - Upgrade SLF4J to 1.7.36</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7489" rel="nofollow">MNG-7489</a>] - Upgrade JUnit to 4.13.2</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7491" rel="nofollow">MNG-7491</a>] - Update parent POM to 36</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7499" rel="nofollow">MNG-7499</a>] - Upgrade Maven Resolver to 1.8.1</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7502" rel="nofollow">MNG-7502</a>] - Upgrade Guice to 5.1.0</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7506" rel="nofollow">MNG-7506</a>] - Upgrade Maven Wagon to 3.5.2</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7522" rel="nofollow">MNG-7522</a>] - Upgrade Maven Resolver to 1.8.2</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7530" rel="nofollow">MNG-7530</a>] - Upgrade Apache Maven parent POM to version 37</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7586" rel="nofollow">MNG-7586</a>] - Update Maven Resolver to 1.9.2</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7613" rel="nofollow">MNG-7613</a>] - Upgrade Apache Maven parent POM to version 38</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7641" rel="nofollow">MNG-7641</a>] - Upgrade Maven Wagon to 3.5.3</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7668" rel="nofollow">MNG-7668</a>] - Update Maven Resolver to 1.9.4</li>\n<li>[<a href="https://issues.apache.org/jira/browse/MNG-7675" rel="nofollow">MNG-7675</a>] - Update Maven Parent to 39</li>\n</ul>', 
'authors': [{'name': 'slawekjaranowski'}], 
'author_detail': {'name': 'slawekjaranowski'}, 
'author': 'slawekjaranowski', 
'media_thumbnail': [
		{'height': '30', 'width': '30', 'url': 'https://avatars.githubusercontent.com/u/3578921?s=60&v=4'}
], 
'href': ''
}
```

## NodeJS Feed

URL

```bash
https://github.com/nodejs/node/releases.atom
```

Key components

```bash
'title': '2023-02-21, Version 19.7.0 (Current), @MylesBorins',
'updated': '2023-02-21T18:18:33Z',
'link': 'https://github.com/nodejs/node/releases/tag/v19.7.0',
'summary': '<h3>Notable Changes</h3>\n<ul>\n<li>[<a href="https://github.com/nodejs/node/commit/60a612607e"><code>60a612607e</code></a>] - <strong>deps</strong>: upgrade npm to 9.5.0 (npm team) <a href="https://github.com/nodejs/node/pull/46673">#46673</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/7d6c27eab1"><code>7d6c27eab1</code></a>] - <strong>deps</strong>: add ada as a dependency (Yagiz Nizipli) <a href="https://github.com/nodejs/node/pull/46410">#46410</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/a79a8bf85a"><code>a79a8bf85a</code></a>] - <strong>doc</strong>: add debadree25 to collaborators (Debadree Chatterjee) <a href="https://github.com/nodejs/node/pull/46716">#46716</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/0c2c322ee6"><code>0c2c322ee6</code></a>] - <strong>doc</strong>: add deokjinkim to collaborators (Deokjin Kim) <a href="https://github.com/nodejs/node/pull/46444">#46444</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/9b23309f53"><code>9b23309f53</code></a>] - <strong>doc,lib,src,test</strong>: rename --test-coverage (Colin Ihrig) <a href="https://github.com/nodejs/node/pull/46017">#46017</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/8590eb4830"><code>8590eb4830</code></a>] - <strong>(SEMVER-MINOR)</strong> <strong>lib</strong>: add aborted() utility function (Debadree Chatterjee) <a href="https://github.com/nodejs/node/pull/46494">#46494</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/164bfe82cc"><code>164bfe82cc</code></a>] - <strong>(SEMVER-MINOR)</strong> <strong>src</strong>: add initial support for single executable applications (Darshan Sen) <a href="https://github.com/nodejs/node/pull/45038">#45038</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/f3908411fd"><code>f3908411fd</code></a>] - <strong>(SEMVER-MINOR)</strong> <strong>src</strong>: allow optional Isolate termination in node::Stop() (Shelley Vohr) <a href="https://github.com/nodejs/node/pull/46583">#46583</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/c34bac2fed"><code>c34bac2fed</code></a>] - <strong>(SEMVER-MINOR)</strong> <strong>src</strong>: allow blobs in addition to <code>FILE*</code>s in embedder snapshot API (Anna Henningsen) <a href="https://github.com/nodejs/node/pull/46491">#46491</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/683a1f8f3e"><code>683a1f8f3e</code></a>] - <strong>(SEMVER-MINOR)</strong> <strong>src</strong>: allow snapshotting from the embedder API (Anna Henningsen) <a href="https://github.com/nodejs/node/pull/45888">#45888</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/658d2f4710"><code>658d2f4710</code></a>] - <strong>(SEMVER-MINOR)</strong> <strong>src</strong>: make build_snapshot a per-Isolate option, rather than a global one (Anna Henningsen) <a href="https://github.com/nodejs/node/pull/45888">#45888</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/6801d3753c"><code>6801d3753c</code></a>] - <strong>(SEMVER-MINOR)</strong> <strong>src</strong>: add snapshot support for embedder API (Anna Henningsen) <a href="https://github.com/nodejs/node/pull/45888">#45888</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/e77d538d32"><code>e77d538d32</code></a>] - <strong>(SEMVER-MINOR)</strong> <strong>src</strong>: allow embedder control of code generation policy (Shelley Vohr) <a href="https://github.com/nodejs/node/pull/46368">#46368</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/633d3f292d"><code>633d3f292d</code></a>] - <strong>(SEMVER-MINOR)</strong> <strong>stream</strong>: add abort signal for ReadableStream and WritableStream (Debadree Chatterjee) <a href="https://github.com/nodejs/node/pull/46273">#46273</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/6119289251"><code>6119289251</code></a>] - <strong>test_runner</strong>: add initial code coverage support (Colin Ihrig) <a href="https://github.com/nodejs/node/pull/46017">#46017</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/a51fe3c663"><code>a51fe3c663</code></a>] - <strong>url</strong>: replace url-parser with ada (Yagiz Nizipli) <a href="https://github.com/nodejs/node/pull/46410">#46410</a></li>\n</ul>\n<h3>Commits</h3>\n<ul>\n<li>[<a href="https://github.com/nodejs/node/commit/731a7ae9da"><code>731a7ae9da</code></a>] - <strong>async_hooks</strong>: add async local storage propagation benchmarks (Chengzhong Wu) <a href="https://github.com/nodejs/node/pull/46414">#46414</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/05ad792a07"><code>05ad792a07</code></a>] - <strong>async_hooks</strong>: remove experimental onPropagate option (James M Snell) <a href="https://github.com/nodejs/node/pull/46386">#46386</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/6b21170b10"><code>6b21170b10</code></a>] - <strong>benchmark</strong>: add trailing commas in <code>benchmark/path</code> (Antoine du Hamel) <a href="https://github.com/nodejs/node/pull/46628">#46628</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/4b89ec409f"><code>4b89ec409f</code></a>] - <strong>benchmark</strong>: add trailing commas in <code>benchmark/http</code> (Antoine du Hamel) <a href="https://github.com/nodejs/node/pull/46609">#46609</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/ff95eb7386"><code>ff95eb7386</code></a>] - <strong>benchmark</strong>: add trailing commas in <code>benchmark/crypto</code> (Antoine du Hamel) <a href="https://github.com/nodejs/node/pull/46553">#46553</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/638d9b8d4b"><code>638d9b8d4b</code></a>] - <strong>benchmark</strong>: add trailing commas in <code>benchmark/url</code> (Antoine du Hamel) <a href="https://github.com/nodejs/node/pull/46551">#46551</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/7524871a9b"><code>7524871a9b</code></a>] - <strong>benchmark</strong>: add trailing commas in <code>benchmark/http2</code> (Antoine du Hamel) <a href="https://github.com/nodejs/node/pull/46552">#46552</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/9d9b3f856f"><code>9d9b3f856f</code></a>] - <strong>benchmark</strong>: add trailing commas in <code>benchmark/process</code> (Antoine du Hamel) <a href="https://github.com/nodejs/node/pull/46481">#46481</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/6c69ad6d43"><code>6c69ad6d43</code></a>] - <strong>benchmark</strong>: add trailing commas in <code>benchmark/misc</code> (Antoine du Hamel) <a href="https://github.com/nodejs/node/pull/46474">#46474</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/7f8b292bee"><code>7f8b292bee</code></a>] - <strong>benchmark</strong>: add trailing commas in <code>benchmark/buffers</code> (Antoine du Hamel) <a href="https://github.com/nodejs/node/pull/46473">#46473</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/897e3c2782"><code>897e3c2782</code></a>] - <strong>benchmark</strong>: add trailing commas in <code>benchmark/module</code> (Antoine du Hamel) <a href="https://github.com/nodejs/node/pull/46461">#46461</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/7760d40c04"><code>7760d40c04</code></a>] - <strong>benchmark</strong>: add trailing commas in <code>benchmark/net</code> (Antoine du Hamel) <a href="https://github.com/nodejs/node/pull/46439">#46439</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/8b88d605ca"><code>8b88d605ca</code></a>] - <strong>benchmark</strong>: add trailing commas in <code>benchmark/util</code> (Antoine du Hamel) <a href="https://github.com/nodejs/node/pull/46438">#46438</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/2c8c9f978d"><code>2c8c9f978d</code></a>] - <strong>benchmark</strong>: add trailing commas in <code>benchmark/async_hooks</code> (Antoine du Hamel) <a href="https://github.com/nodejs/node/pull/46424">#46424</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/b364b9bd60"><code>b364b9bd60</code></a>] - <strong>benchmark</strong>: add trailing commas in <code>benchmark/fs</code> (Antoine du Hamel) <a href="https://github.com/nodejs/node/pull/46426">#46426</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/e15ddba7e7"><code>e15ddba7e7</code></a>] - <strong>build</strong>: add GitHub Action for coverage with --without-intl (Rich Trott) <a href="https://github.com/nodejs/node/pull/37954">#37954</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/c781a48097"><code>c781a48097</code></a>] - <strong>build</strong>: do not disable inspector when intl is disabled (Rich Trott) <a href="https://github.com/nodejs/node/pull/37954">#37954</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/b4deb2fcd5"><code>b4deb2fcd5</code></a>] - <strong>crypto</strong>: don\'t assume FIPS is disabled by default (Michael Dawson) <a href="https://github.com/nodejs/node/pull/46532">#46532</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/60a612607e"><code>60a612607e</code></a>] - <strong>deps</strong>: upgrade npm to 9.5.0 (npm team) <a href="https://github.com/nodejs/node/pull/46673">#46673</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/6c997035fc"><code>6c997035fc</code></a>] - <strong>deps</strong>: update corepack to 0.16.0 (Node.js GitHub Bot) <a href="https://github.com/nodejs/node/pull/46710">#46710</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/2ed3875eee"><code>2ed3875eee</code></a>] - <strong>deps</strong>: update undici to 5.20.0 (Node.js GitHub Bot) <a href="https://github.com/nodejs/node/pull/46711">#46711</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/20cb13bf7f"><code>20cb13bf7f</code></a>] - <strong>deps</strong>: update ada to v1.0.1 (Yagiz Nizipli) <a href="https://github.com/nodejs/node/pull/46550">#46550</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/c0983cfc06"><code>c0983cfc06</code></a>] - <strong>deps</strong>: copy <code>postject-api.h</code> and <code>LICENSE</code> to the <code>deps</code> folder (Darshan Sen) <a href="https://github.com/nodejs/node/pull/46582">#46582</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/7d6c27eab1"><code>7d6c27eab1</code></a>] - <strong>deps</strong>: add ada as a dependency (Yagiz Nizipli) <a href="https://github.com/nodejs/node/pull/46410">#46410</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/7e7e2d037b"><code>7e7e2d037b</code></a>] - <strong>deps</strong>: update c-ares to 1.19.0 (Michaël Zasso) <a href="https://github.com/nodejs/node/pull/46415">#46415</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/a79a8bf85a"><code>a79a8bf85a</code></a>] - <strong>doc</strong>: add debadree25 to collaborators (Debadree Chatterjee) <a href="https://github.com/nodejs/node/pull/46716">#46716</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/6a8b04d709"><code>6a8b04d709</code></a>] - <strong>doc</strong>: move bcoe to emeriti (Benjamin Coe) <a href="https://github.com/nodejs/node/pull/46703">#46703</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/a0a6ee0f54"><code>a0a6ee0f54</code></a>] - <strong>doc</strong>: add response.strictContentLength to documentation (Marco Ippolito) <a href="https://github.com/nodejs/node/pull/46627">#46627</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/ffdd64dce3"><code>ffdd64dce3</code></a>] - <strong>doc</strong>: remove unused functions from example of <code>streamConsumers.text</code> (Deokjin Kim) <a href="https://github.com/nodejs/node/pull/46581">#46581</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/c771d66864"><code>c771d66864</code></a>] - <strong>doc</strong>: fix test runner examples (Richie McColl) <a href="https://github.com/nodejs/node/pull/46565">#46565</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/375bb22df9"><code>375bb22df9</code></a>] - <strong>doc</strong>: update test concurrency description / default values (richiemccoll) <a href="https://github.com/nodejs/node/pull/46457">#46457</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/a7beac04ba"><code>a7beac04ba</code></a>] - <strong>doc</strong>: enrich test command with executable (Tony Gorez) <a href="https://github.com/nodejs/node/pull/44347">#44347</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/aef57cd290"><code>aef57cd290</code></a>] - <strong>doc</strong>: fix wrong location of <code>requestTimeout</code>\'s default value (Deokjin Kim) <a href="https://github.com/nodejs/node/pull/46423">#46423</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/0c2c322ee6"><code>0c2c322ee6</code></a>] - <strong>doc</strong>: add deokjinkim to collaborators (Deokjin Kim) <a href="https://github.com/nodejs/node/pull/46444">#46444</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/31d3e3c486"><code>31d3e3c486</code></a>] - <strong>doc</strong>: fix -C flag usage (三咲智子 Kevin Deng) <a href="https://github.com/nodejs/node/pull/46388">#46388</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/905a6756a3"><code>905a6756a3</code></a>] - <strong>doc</strong>: add note about major release rotation (Rafael Gonzaga) <a href="https://github.com/nodejs/node/pull/46436">#46436</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/33a98c42fa"><code>33a98c42fa</code></a>] - <strong>doc</strong>: update threat model based on discussions (Michael Dawson) <a href="https://github.com/nodejs/node/pull/46373">#46373</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/9b23309f53"><code>9b23309f53</code></a>] - <strong>doc,lib,src,test</strong>: rename --test-coverage (Colin Ihrig) <a href="https://github.com/nodejs/node/pull/46017">#46017</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/f192b83800"><code>f192b83800</code></a>] - <strong>esm</strong>: misc test refactors (Geoffrey Booth) <a href="https://github.com/nodejs/node/pull/46631">#46631</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/7f2cdd36cf"><code>7f2cdd36cf</code></a>] - <strong>http</strong>: add note about clientError event (Paolo Insogna) <a href="https://github.com/nodejs/node/pull/46584">#46584</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/d8c527f24f"><code>d8c527f24f</code></a>] - <strong>http</strong>: use v8::Array::New() with a prebuilt vector (Joyee Cheung) <a href="https://github.com/nodejs/node/pull/46447">#46447</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/fa600fe003"><code>fa600fe003</code></a>] - <strong>lib</strong>: add trailing commas in <code>internal/process</code> (Antoine du Hamel) <a href="https://github.com/nodejs/node/pull/46687">#46687</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/4aebee63f0"><code>4aebee63f0</code></a>] - <strong>lib</strong>: do not crash using workers with disabled shared array buffers (Ruben Bridgewater) <a href="https://github.com/nodejs/node/pull/41023">#41023</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/a740908588"><code>a740908588</code></a>] - <strong>lib</strong>: delete module findPath unused params (sinkhaha) <a href="https://github.com/nodejs/node/pull/45371">#45371</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/8b46c763d9"><code>8b46c763d9</code></a>] - <strong>lib</strong>: enforce use of trailing commas in more files (Antoine du Hamel) <a href="https://github.com/nodejs/node/pull/46655">#46655</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/aae0020e27"><code>aae0020e27</code></a>] - <strong>lib</strong>: enforce use of trailing commas for functions (Antoine du Hamel) <a href="https://github.com/nodejs/node/pull/46629">#46629</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/da9ebaf138"><code>da9ebaf138</code></a>] - <strong>lib</strong>: predeclare Event.isTrusted prop descriptor (Santiago Gimeno) <a href="https://github.com/nodejs/node/pull/46527">#46527</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/35570e970e"><code>35570e970e</code></a>] - <strong>lib</strong>: tighten <code>AbortSignal.prototype.throwIfAborted</code> implementation (Antoine du Hamel) <a href="https://github.com/nodejs/node/pull/46521">#46521</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/8590eb4830"><code>8590eb4830</code></a>] - <strong>(SEMVER-MINOR)</strong> <strong>lib</strong>: add aborted() utility function (Debadree Chatterjee) <a href="https://github.com/nodejs/node/pull/46494">#46494</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/5d1a729f76"><code>5d1a729f76</code></a>] - <strong>meta</strong>: update AUTHORS (Node.js GitHub Bot) <a href="https://github.com/nodejs/node/pull/46624">#46624</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/cb9b9ad879"><code>cb9b9ad879</code></a>] - <strong>meta</strong>: move one or more collaborators to emeritus (Node.js GitHub Bot) <a href="https://github.com/nodejs/node/pull/46513">#46513</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/17b82c85d9"><code>17b82c85d9</code></a>] - <strong>meta</strong>: update AUTHORS (Node.js GitHub Bot) <a href="https://github.com/nodejs/node/pull/46504">#46504</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/bb14a2b098"><code>bb14a2b098</code></a>] - <strong>meta</strong>: move one or more collaborators to emeritus (Node.js GitHub Bot) <a href="https://github.com/nodejs/node/pull/46411">#46411</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/152a3c7d1d"><code>152a3c7d1d</code></a>] - <strong>process</strong>: print versions by sort (Himself65) <a href="https://github.com/nodejs/node/pull/46428">#46428</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/164bfe82cc"><code>164bfe82cc</code></a>] - <strong>(SEMVER-MINOR)</strong> <strong>src</strong>: add initial support for single executable applications (Darshan Sen) <a href="https://github.com/nodejs/node/pull/45038">#45038</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/f3908411fd"><code>f3908411fd</code></a>] - <strong>(SEMVER-MINOR)</strong> <strong>src</strong>: allow optional Isolate termination in node::Stop() (Shelley Vohr) <a href="https://github.com/nodejs/node/pull/46583">#46583</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/bdba600d32"><code>bdba600d32</code></a>] - <strong>src</strong>: remove icu usage from node_string.cc (Yagiz Nizipli) <a href="https://github.com/nodejs/node/pull/46548">#46548</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/31fb2e22a0"><code>31fb2e22a0</code></a>] - <strong>src</strong>: add fflush() to SnapshotData::ToFile() (Anna Henningsen) <a href="https://github.com/nodejs/node/pull/46531">#46531</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/c34bac2fed"><code>c34bac2fed</code></a>] - <strong>(SEMVER-MINOR)</strong> <strong>src</strong>: allow blobs in addition to <code>FILE*</code>s in embedder snapshot API (Anna Henningsen) <a href="https://github.com/nodejs/node/pull/46491">#46491</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/c3325bfc0d"><code>c3325bfc0d</code></a>] - <strong>src</strong>: make edge names in BaseObjects more descriptive in heap snapshots (Joyee Cheung) <a href="https://github.com/nodejs/node/pull/46492">#46492</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/3c5db8f419"><code>3c5db8f419</code></a>] - <strong>src</strong>: avoid leaking snapshot fp on error (Tobias Nießen) <a href="https://github.com/nodejs/node/pull/46497">#46497</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/1a808a4aad"><code>1a808a4aad</code></a>] - <strong>src</strong>: check return value of ftell() (Tobias Nießen) <a href="https://github.com/nodejs/node/pull/46495">#46495</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/f72f643549"><code>f72f643549</code></a>] - <strong>src</strong>: remove unused includes from main thread (Yagiz Nizipli) <a href="https://github.com/nodejs/node/pull/46471">#46471</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/60c2a863da"><code>60c2a863da</code></a>] - <strong>src</strong>: use string_view instead of std::string&amp; (Yagiz Nizipli) <a href="https://github.com/nodejs/node/pull/46471">#46471</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/f35f6d2218"><code>f35f6d2218</code></a>] - <strong>src</strong>: use simdutf utf8 to utf16 instead of icu (Yagiz Nizipli) <a href="https://github.com/nodejs/node/pull/46471">#46471</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/00b81c7afe"><code>00b81c7afe</code></a>] - <strong>src</strong>: replace icu with simdutf for char counts (Yagiz Nizipli) <a href="https://github.com/nodejs/node/pull/46472">#46472</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/683a1f8f3e"><code>683a1f8f3e</code></a>] - <strong>(SEMVER-MINOR)</strong> <strong>src</strong>: allow snapshotting from the embedder API (Anna Henningsen) <a href="https://github.com/nodejs/node/pull/45888">#45888</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/658d2f4710"><code>658d2f4710</code></a>] - <strong>(SEMVER-MINOR)</strong> <strong>src</strong>: make build_snapshot a per-Isolate option, rather than a global one (Anna Henningsen) <a href="https://github.com/nodejs/node/pull/45888">#45888</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/6801d3753c"><code>6801d3753c</code></a>] - <strong>(SEMVER-MINOR)</strong> <strong>src</strong>: add snapshot support for embedder API (Anna Henningsen) <a href="https://github.com/nodejs/node/pull/45888">#45888</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/95065c3185"><code>95065c3185</code></a>] - <strong>src</strong>: add additional utilities to crypto::SecureContext (James M Snell) <a href="https://github.com/nodejs/node/pull/45912">#45912</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/efc59d0843"><code>efc59d0843</code></a>] - <strong>src</strong>: add KeyObjectHandle::HasInstance (James M Snell) <a href="https://github.com/nodejs/node/pull/45912">#45912</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/a8a2d0e2b1"><code>a8a2d0e2b1</code></a>] - <strong>src</strong>: add GetCurrentCipherName/Version to crypto_common (James M Snell) <a href="https://github.com/nodejs/node/pull/45912">#45912</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/6cf860d3d6"><code>6cf860d3d6</code></a>] - <strong>src</strong>: back snapshot I/O with a std::vector sink (Joyee Cheung) <a href="https://github.com/nodejs/node/pull/46463">#46463</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/e77d538d32"><code>e77d538d32</code></a>] - <strong>(SEMVER-MINOR)</strong> <strong>src</strong>: allow embedder control of code generation policy (Shelley Vohr) <a href="https://github.com/nodejs/node/pull/46368">#46368</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/7756438c81"><code>7756438c81</code></a>] - <strong>stream</strong>: add trailing commas in webstream source files (Antoine du Hamel) <a href="https://github.com/nodejs/node/pull/46685">#46685</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/6b64a945c6"><code>6b64a945c6</code></a>] - <strong>stream</strong>: add trailing commas in stream source files (Antoine du Hamel) <a href="https://github.com/nodejs/node/pull/46686">#46686</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/633d3f292d"><code>633d3f292d</code></a>] - <strong>(SEMVER-MINOR)</strong> <strong>stream</strong>: add abort signal for ReadableStream and WritableStream (Debadree Chatterjee) <a href="https://github.com/nodejs/node/pull/46273">#46273</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/f91260b32a"><code>f91260b32a</code></a>] - <strong>stream</strong>: refactor to use <code>validateAbortSignal</code> (Antoine du Hamel) <a href="https://github.com/nodejs/node/pull/46520">#46520</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/6bf7388b62"><code>6bf7388b62</code></a>] - <strong>stream</strong>: allow transfer of readable byte streams (MrBBot) <a href="https://github.com/nodejs/node/pull/45955">#45955</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/c2068537fa"><code>c2068537fa</code></a>] - <strong>stream</strong>: add pipeline() for webstreams (Debadree Chatterjee) <a href="https://github.com/nodejs/node/pull/46307">#46307</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/4cf4b41c56"><code>4cf4b41c56</code></a>] - <strong>stream</strong>: add suport for abort signal in finished() for webstreams (Debadree Chatterjee) <a href="https://github.com/nodejs/node/pull/46403">#46403</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/b844a09fa5"><code>b844a09fa5</code></a>] - <strong>stream</strong>: dont access Object.prototype.type during TransformStream init (Debadree Chatterjee) <a href="https://github.com/nodejs/node/pull/46389">#46389</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/6ad01fd7b5"><code>6ad01fd7b5</code></a>] - <strong>test</strong>: fix <code>test-net-autoselectfamily</code> for kernel without IPv6 support (Livia Medeiros) <a href="https://github.com/nodejs/node/pull/45856">#45856</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/2239e24306"><code>2239e24306</code></a>] - <strong>test</strong>: fix assertions in test-snapshot-dns-lookup* (Tobias Nießen) <a href="https://github.com/nodejs/node/pull/46618">#46618</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/c4ca98e786"><code>c4ca98e786</code></a>] - <strong>test</strong>: cover publicExponent validation in OpenSSL (Tobias Nießen) <a href="https://github.com/nodejs/node/pull/46632">#46632</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/e60d3f2b1d"><code>e60d3f2b1d</code></a>] - <strong>test</strong>: add WPTRunner support for variants and generating WPT reports (Filip Skokan) <a href="https://github.com/nodejs/node/pull/46498">#46498</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/217f2f6e2a"><code>217f2f6e2a</code></a>] - <strong>test</strong>: add trailing commas in <code>test/pummel</code> (Antoine du Hamel) <a href="https://github.com/nodejs/node/pull/46610">#46610</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/641e1771c8"><code>641e1771c8</code></a>] - <strong>test</strong>: enable api-invalid-label.any.js in encoding WPTs (Filip Skokan) <a href="https://github.com/nodejs/node/pull/46506">#46506</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/89aa161173"><code>89aa161173</code></a>] - <strong>test</strong>: fix tap parser fails if a test logs a number (Pulkit Gupta) <a href="https://github.com/nodejs/node/pull/46056">#46056</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/faba8d4a30"><code>faba8d4a30</code></a>] - <strong>test</strong>: add trailing commas in <code>test/js-native-api</code> (Antoine du Hamel) <a href="https://github.com/nodejs/node/pull/46385">#46385</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/d556ccdd26"><code>d556ccdd26</code></a>] - <strong>test</strong>: make more crypto tests work with BoringSSL (Shelley Vohr) <a href="https://github.com/nodejs/node/pull/46429">#46429</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/c7f29b24a6"><code>c7f29b24a6</code></a>] - <strong>test</strong>: add trailing commas in <code>test/known_issues</code> (Antoine du Hamel) <a href="https://github.com/nodejs/node/pull/46408">#46408</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/a66e7ca6c5"><code>a66e7ca6c5</code></a>] - <strong>test</strong>: add trailing commas in <code>test/internet</code> (Antoine du Hamel) <a href="https://github.com/nodejs/node/pull/46407">#46407</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/0f75633086"><code>0f75633086</code></a>] - <strong>test,crypto</strong>: update WebCryptoAPI WPT (Filip Skokan) <a href="https://github.com/nodejs/node/pull/46575">#46575</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/ddf5002782"><code>ddf5002782</code></a>] - <strong>test_runner</strong>: parse non-ascii character correctly (Mert Can Altın) <a href="https://github.com/nodejs/node/pull/45736">#45736</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/5b748114d2"><code>5b748114d2</code></a>] - <strong>test_runner</strong>: allow nesting test within describe (Moshe Atlow) <a href="https://github.com/nodejs/node/pull/46544">#46544</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/c526f9f70a"><code>c526f9f70a</code></a>] - <strong>test_runner</strong>: fix missing test diagnostics (Moshe Atlow) <a href="https://github.com/nodejs/node/pull/46450">#46450</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/b31aabb101"><code>b31aabb101</code></a>] - <strong>test_runner</strong>: top-level diagnostics not ommited when running with --test (Pulkit Gupta) <a href="https://github.com/nodejs/node/pull/46441">#46441</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/6119289251"><code>6119289251</code></a>] - <strong>test_runner</strong>: add initial code coverage support (Colin Ihrig) <a href="https://github.com/nodejs/node/pull/46017">#46017</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/6f24f0621e"><code>6f24f0621e</code></a>] - <strong>timers</strong>: cleanup no-longer relevant TODOs in timers/promises (James M Snell) <a href="https://github.com/nodejs/node/pull/46499">#46499</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/1cd22e7d19"><code>1cd22e7d19</code></a>] - <strong>tools</strong>: fix bug in <code>prefer-primordials</code> lint rule (Antoine du Hamel) <a href="https://github.com/nodejs/node/pull/46659">#46659</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/87df34ac28"><code>87df34ac28</code></a>] - <strong>tools</strong>: fix update-ada script (Yagiz Nizipli) <a href="https://github.com/nodejs/node/pull/46550">#46550</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/f62b58a623"><code>f62b58a623</code></a>] - <strong>tools</strong>: add a daily wpt.fyi synchronized report upload (Filip Skokan) <a href="https://github.com/nodejs/node/pull/46498">#46498</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/803f00aa32"><code>803f00aa32</code></a>] - <strong>tools</strong>: update eslint to 8.34.0 (Node.js GitHub Bot) <a href="https://github.com/nodejs/node/pull/46625">#46625</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/f87216bdb2"><code>f87216bdb2</code></a>] - <strong>tools</strong>: update lint-md-dependencies to rollup@3.15.0 to-vfile@7.2.4 (Node.js GitHub Bot) <a href="https://github.com/nodejs/node/pull/46623">#46623</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/8ee9e48560"><code>8ee9e48560</code></a>] - <strong>tools</strong>: update doc to remark-html@15.0.2 to-vfile@7.2.4 (Node.js GitHub Bot) <a href="https://github.com/nodejs/node/pull/46622">#46622</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/148c5d9239"><code>148c5d9239</code></a>] - <strong>tools</strong>: update lint-md-dependencies to rollup@3.13.0 vfile-reporter@7.0.5 (Node.js GitHub Bot) <a href="https://github.com/nodejs/node/pull/46503">#46503</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/51c6c61a58"><code>51c6c61a58</code></a>] - <strong>tools</strong>: update ESLint custom rules to not use the deprecated format (Antoine du Hamel) <a href="https://github.com/nodejs/node/pull/46460">#46460</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/a51fe3c663"><code>a51fe3c663</code></a>] - <strong>url</strong>: replace url-parser with ada (Yagiz Nizipli) <a href="https://github.com/nodejs/node/pull/46410">#46410</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/129c9e7180"><code>129c9e7180</code></a>] - <strong>url</strong>: remove unused <code>URL::ToFilePath()</code> (Yagiz Nizipli) <a href="https://github.com/nodejs/node/pull/46487">#46487</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/9a604d67c3"><code>9a604d67c3</code></a>] - <strong>url</strong>: remove unused <code>URL::toObject</code> (Yagiz Nizipli) <a href="https://github.com/nodejs/node/pull/46486">#46486</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/d6fbebda54"><code>d6fbebda54</code></a>] - <strong>url</strong>: remove unused <code>setURLConstructor</code> function (Yagiz Nizipli) <a href="https://github.com/nodejs/node/pull/46485">#46485</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/17b3ee33c2"><code>17b3ee33c2</code></a>] - <strong>vm</strong>: properly support symbols on globals (Nicolas DUBIEN) <a href="https://github.com/nodejs/node/pull/46458">#46458</a></li>\n</ul>',
```

Constraint

- Cannot filter pre-releases as there is no identifier within entry to distinguish release types
    - Requires Gitlab API

raw sample rss entry

```bash
{
'id': 'tag:github.com,2008:Repository/27193779/v19.7.0', 
'guidislink': True, 
'link': 'https://github.com/nodejs/node/releases/tag/v19.7.0', 
'updated': '2023-02-21T18:18:33Z', 
'updated_parsed': 
		time.struct_time(
				tm_year=2023, 
				tm_mon=2, 
				tm_mday=21, 
				tm_hour=18, 
				tm_min=18, 
				tm_sec=33, 
				tm_wday=1, 
				tm_yday=52, 
				tm_isdst=0), 
'links': [
		{'rel': 'alternate', 'type': 'text/html', 
			'href': 'https://github.com/nodejs/node/releases/tag/v19.7.0'}
], 
'title': '2023-02-21, Version 19.7.0 (Current), @MylesBorins', 
'title_detail': 
		{'type': 'text/plain', 
			'language': 'en-US', 
			'base': 'https://github.com/nodejs/node/releases.atom', 
			'value': '2023-02-21, Version 19.7.0 (Current), @MylesBorins'}, 
'content': [
		{'type': 'text/html', 
			'language': 'en-US', 
			'base': 'https://github.com/nodejs/node/releases.atom', 
			'value': '<h3>Notable Changes</h3>\n<ul>\n<li>[<a href="https://github.com/nodejs/node/commit/60a612607e"><code>60a612607e</code></a>] - <strong>deps</strong>: upgrade npm to 9.5.0 (npm team) <a href="https://github.com/nodejs/node/pull/46673">#46673</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/7d6c27eab1"><code>7d6c27eab1</code></a>] - <strong>deps</strong>: add ada as a dependency (Yagiz Nizipli) <a href="https://github.com/nodejs/node/pull/46410">#46410</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/a79a8bf85a"><code>a79a8bf85a</code></a>] - <strong>doc</strong>: add debadree25 to collaborators (Debadree Chatterjee) <a href="https://github.com/nodejs/node/pull/46716">#46716</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/0c2c322ee6"><code>0c2c322ee6</code></a>] - <strong>doc</strong>: add deokjinkim to collaborators (Deokjin Kim) <a href="https://github.com/nodejs/node/pull/46444">#46444</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/9b23309f53"><code>9b23309f53</code></a>] - <strong>doc,lib,src,test</strong>: rename --test-coverage (Colin Ihrig) <a href="https://github.com/nodejs/node/pull/46017">#46017</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/8590eb4830"><code>8590eb4830</code></a>] - <strong>(SEMVER-MINOR)</strong> <strong>lib</strong>: add aborted() utility function (Debadree Chatterjee) <a href="https://github.com/nodejs/node/pull/46494">#46494</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/164bfe82cc"><code>164bfe82cc</code></a>] - <strong>(SEMVER-MINOR)</strong> <strong>src</strong>: add initial support for single executable applications (Darshan Sen) <a href="https://github.com/nodejs/node/pull/45038">#45038</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/f3908411fd"><code>f3908411fd</code></a>] - <strong>(SEMVER-MINOR)</strong> <strong>src</strong>: allow optional Isolate termination in node::Stop() (Shelley Vohr) <a href="https://github.com/nodejs/node/pull/46583">#46583</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/c34bac2fed"><code>c34bac2fed</code></a>] - <strong>(SEMVER-MINOR)</strong> <strong>src</strong>: allow blobs in addition to <code>FILE*</code>s in embedder snapshot API (Anna Henningsen) <a href="https://github.com/nodejs/node/pull/46491">#46491</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/683a1f8f3e"><code>683a1f8f3e</code></a>] - <strong>(SEMVER-MINOR)</strong> <strong>src</strong>: allow snapshotting from the embedder API (Anna Henningsen) <a href="https://github.com/nodejs/node/pull/45888">#45888</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/658d2f4710"><code>658d2f4710</code></a>] - <strong>(SEMVER-MINOR)</strong> <strong>src</strong>: make build_snapshot a per-Isolate option, rather than a global one (Anna Henningsen) <a href="https://github.com/nodejs/node/pull/45888">#45888</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/6801d3753c"><code>6801d3753c</code></a>] - <strong>(SEMVER-MINOR)</strong> <strong>src</strong>: add snapshot support for embedder API (Anna Henningsen) <a href="https://github.com/nodejs/node/pull/45888">#45888</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/e77d538d32"><code>e77d538d32</code></a>] - <strong>(SEMVER-MINOR)</strong> <strong>src</strong>: allow embedder control of code generation policy (Shelley Vohr) <a href="https://github.com/nodejs/node/pull/46368">#46368</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/633d3f292d"><code>633d3f292d</code></a>] - <strong>(SEMVER-MINOR)</strong> <strong>stream</strong>: add abort signal for ReadableStream and WritableStream (Debadree Chatterjee) <a href="https://github.com/nodejs/node/pull/46273">#46273</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/6119289251"><code>6119289251</code></a>] - <strong>test_runner</strong>: add initial code coverage support (Colin Ihrig) <a href="https://github.com/nodejs/node/pull/46017">#46017</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/a51fe3c663"><code>a51fe3c663</code></a>] - <strong>url</strong>: replace url-parser with ada (Yagiz Nizipli) <a href="https://github.com/nodejs/node/pull/46410">#46410</a></li>\n</ul>\n<h3>Commits</h3>\n<ul>\n<li>[<a href="https://github.com/nodejs/node/commit/731a7ae9da"><code>731a7ae9da</code></a>] - <strong>async_hooks</strong>: add async local storage propagation benchmarks (Chengzhong Wu) <a href="https://github.com/nodejs/node/pull/46414">#46414</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/05ad792a07"><code>05ad792a07</code></a>] - <strong>async_hooks</strong>: remove experimental onPropagate option (James M Snell) <a href="https://github.com/nodejs/node/pull/46386">#46386</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/6b21170b10"><code>6b21170b10</code></a>] - <strong>benchmark</strong>: add trailing commas in <code>benchmark/path</code> (Antoine du Hamel) <a href="https://github.com/nodejs/node/pull/46628">#46628</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/4b89ec409f"><code>4b89ec409f</code></a>] - <strong>benchmark</strong>: add trailing commas in <code>benchmark/http</code> (Antoine du Hamel) <a href="https://github.com/nodejs/node/pull/46609">#46609</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/ff95eb7386"><code>ff95eb7386</code></a>] - <strong>benchmark</strong>: add trailing commas in <code>benchmark/crypto</code> (Antoine du Hamel) <a href="https://github.com/nodejs/node/pull/46553">#46553</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/638d9b8d4b"><code>638d9b8d4b</code></a>] - <strong>benchmark</strong>: add trailing commas in <code>benchmark/url</code> (Antoine du Hamel) <a href="https://github.com/nodejs/node/pull/46551">#46551</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/7524871a9b"><code>7524871a9b</code></a>] - <strong>benchmark</strong>: add trailing commas in <code>benchmark/http2</code> (Antoine du Hamel) <a href="https://github.com/nodejs/node/pull/46552">#46552</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/9d9b3f856f"><code>9d9b3f856f</code></a>] - <strong>benchmark</strong>: add trailing commas in <code>benchmark/process</code> (Antoine du Hamel) <a href="https://github.com/nodejs/node/pull/46481">#46481</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/6c69ad6d43"><code>6c69ad6d43</code></a>] - <strong>benchmark</strong>: add trailing commas in <code>benchmark/misc</code> (Antoine du Hamel) <a href="https://github.com/nodejs/node/pull/46474">#46474</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/7f8b292bee"><code>7f8b292bee</code></a>] - <strong>benchmark</strong>: add trailing commas in <code>benchmark/buffers</code> (Antoine du Hamel) <a href="https://github.com/nodejs/node/pull/46473">#46473</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/897e3c2782"><code>897e3c2782</code></a>] - <strong>benchmark</strong>: add trailing commas in <code>benchmark/module</code> (Antoine du Hamel) <a href="https://github.com/nodejs/node/pull/46461">#46461</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/7760d40c04"><code>7760d40c04</code></a>] - <strong>benchmark</strong>: add trailing commas in <code>benchmark/net</code> (Antoine du Hamel) <a href="https://github.com/nodejs/node/pull/46439">#46439</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/8b88d605ca"><code>8b88d605ca</code></a>] - <strong>benchmark</strong>: add trailing commas in <code>benchmark/util</code> (Antoine du Hamel) <a href="https://github.com/nodejs/node/pull/46438">#46438</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/2c8c9f978d"><code>2c8c9f978d</code></a>] - <strong>benchmark</strong>: add trailing commas in <code>benchmark/async_hooks</code> (Antoine du Hamel) <a href="https://github.com/nodejs/node/pull/46424">#46424</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/b364b9bd60"><code>b364b9bd60</code></a>] - <strong>benchmark</strong>: add trailing commas in <code>benchmark/fs</code> (Antoine du Hamel) <a href="https://github.com/nodejs/node/pull/46426">#46426</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/e15ddba7e7"><code>e15ddba7e7</code></a>] - <strong>build</strong>: add GitHub Action for coverage with --without-intl (Rich Trott) <a href="https://github.com/nodejs/node/pull/37954">#37954</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/c781a48097"><code>c781a48097</code></a>] - <strong>build</strong>: do not disable inspector when intl is disabled (Rich Trott) <a href="https://github.com/nodejs/node/pull/37954">#37954</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/b4deb2fcd5"><code>b4deb2fcd5</code></a>] - <strong>crypto</strong>: don\'t assume FIPS is disabled by default (Michael Dawson) <a href="https://github.com/nodejs/node/pull/46532">#46532</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/60a612607e"><code>60a612607e</code></a>] - <strong>deps</strong>: upgrade npm to 9.5.0 (npm team) <a href="https://github.com/nodejs/node/pull/46673">#46673</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/6c997035fc"><code>6c997035fc</code></a>] - <strong>deps</strong>: update corepack to 0.16.0 (Node.js GitHub Bot) <a href="https://github.com/nodejs/node/pull/46710">#46710</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/2ed3875eee"><code>2ed3875eee</code></a>] - <strong>deps</strong>: update undici to 5.20.0 (Node.js GitHub Bot) <a href="https://github.com/nodejs/node/pull/46711">#46711</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/20cb13bf7f"><code>20cb13bf7f</code></a>] - <strong>deps</strong>: update ada to v1.0.1 (Yagiz Nizipli) <a href="https://github.com/nodejs/node/pull/46550">#46550</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/c0983cfc06"><code>c0983cfc06</code></a>] - <strong>deps</strong>: copy <code>postject-api.h</code> and <code>LICENSE</code> to the <code>deps</code> folder (Darshan Sen) <a href="https://github.com/nodejs/node/pull/46582">#46582</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/7d6c27eab1"><code>7d6c27eab1</code></a>] - <strong>deps</strong>: add ada as a dependency (Yagiz Nizipli) <a href="https://github.com/nodejs/node/pull/46410">#46410</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/7e7e2d037b"><code>7e7e2d037b</code></a>] - <strong>deps</strong>: update c-ares to 1.19.0 (Michaël Zasso) <a href="https://github.com/nodejs/node/pull/46415">#46415</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/a79a8bf85a"><code>a79a8bf85a</code></a>] - <strong>doc</strong>: add debadree25 to collaborators (Debadree Chatterjee) <a href="https://github.com/nodejs/node/pull/46716">#46716</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/6a8b04d709"><code>6a8b04d709</code></a>] - <strong>doc</strong>: move bcoe to emeriti (Benjamin Coe) <a href="https://github.com/nodejs/node/pull/46703">#46703</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/a0a6ee0f54"><code>a0a6ee0f54</code></a>] - <strong>doc</strong>: add response.strictContentLength to documentation (Marco Ippolito) <a href="https://github.com/nodejs/node/pull/46627">#46627</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/ffdd64dce3"><code>ffdd64dce3</code></a>] - <strong>doc</strong>: remove unused functions from example of <code>streamConsumers.text</code> (Deokjin Kim) <a href="https://github.com/nodejs/node/pull/46581">#46581</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/c771d66864"><code>c771d66864</code></a>] - <strong>doc</strong>: fix test runner examples (Richie McColl) <a href="https://github.com/nodejs/node/pull/46565">#46565</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/375bb22df9"><code>375bb22df9</code></a>] - <strong>doc</strong>: update test concurrency description / default values (richiemccoll) <a href="https://github.com/nodejs/node/pull/46457">#46457</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/a7beac04ba"><code>a7beac04ba</code></a>] - <strong>doc</strong>: enrich test command with executable (Tony Gorez) <a href="https://github.com/nodejs/node/pull/44347">#44347</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/aef57cd290"><code>aef57cd290</code></a>] - <strong>doc</strong>: fix wrong location of <code>requestTimeout</code>\'s default value (Deokjin Kim) <a href="https://github.com/nodejs/node/pull/46423">#46423</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/0c2c322ee6"><code>0c2c322ee6</code></a>] - <strong>doc</strong>: add deokjinkim to collaborators (Deokjin Kim) <a href="https://github.com/nodejs/node/pull/46444">#46444</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/31d3e3c486"><code>31d3e3c486</code></a>] - <strong>doc</strong>: fix -C flag usage (三咲智子 Kevin Deng) <a href="https://github.com/nodejs/node/pull/46388">#46388</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/905a6756a3"><code>905a6756a3</code></a>] - <strong>doc</strong>: add note about major release rotation (Rafael Gonzaga) <a href="https://github.com/nodejs/node/pull/46436">#46436</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/33a98c42fa"><code>33a98c42fa</code></a>] - <strong>doc</strong>: update threat model based on discussions (Michael Dawson) <a href="https://github.com/nodejs/node/pull/46373">#46373</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/9b23309f53"><code>9b23309f53</code></a>] - <strong>doc,lib,src,test</strong>: rename --test-coverage (Colin Ihrig) <a href="https://github.com/nodejs/node/pull/46017">#46017</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/f192b83800"><code>f192b83800</code></a>] - <strong>esm</strong>: misc test refactors (Geoffrey Booth) <a href="https://github.com/nodejs/node/pull/46631">#46631</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/7f2cdd36cf"><code>7f2cdd36cf</code></a>] - <strong>http</strong>: add note about clientError event (Paolo Insogna) <a href="https://github.com/nodejs/node/pull/46584">#46584</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/d8c527f24f"><code>d8c527f24f</code></a>] - <strong>http</strong>: use v8::Array::New() with a prebuilt vector (Joyee Cheung) <a href="https://github.com/nodejs/node/pull/46447">#46447</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/fa600fe003"><code>fa600fe003</code></a>] - <strong>lib</strong>: add trailing commas in <code>internal/process</code> (Antoine du Hamel) <a href="https://github.com/nodejs/node/pull/46687">#46687</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/4aebee63f0"><code>4aebee63f0</code></a>] - <strong>lib</strong>: do not crash using workers with disabled shared array buffers (Ruben Bridgewater) <a href="https://github.com/nodejs/node/pull/41023">#41023</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/a740908588"><code>a740908588</code></a>] - <strong>lib</strong>: delete module findPath unused params (sinkhaha) <a href="https://github.com/nodejs/node/pull/45371">#45371</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/8b46c763d9"><code>8b46c763d9</code></a>] - <strong>lib</strong>: enforce use of trailing commas in more files (Antoine du Hamel) <a href="https://github.com/nodejs/node/pull/46655">#46655</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/aae0020e27"><code>aae0020e27</code></a>] - <strong>lib</strong>: enforce use of trailing commas for functions (Antoine du Hamel) <a href="https://github.com/nodejs/node/pull/46629">#46629</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/da9ebaf138"><code>da9ebaf138</code></a>] - <strong>lib</strong>: predeclare Event.isTrusted prop descriptor (Santiago Gimeno) <a href="https://github.com/nodejs/node/pull/46527">#46527</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/35570e970e"><code>35570e970e</code></a>] - <strong>lib</strong>: tighten <code>AbortSignal.prototype.throwIfAborted</code> implementation (Antoine du Hamel) <a href="https://github.com/nodejs/node/pull/46521">#46521</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/8590eb4830"><code>8590eb4830</code></a>] - <strong>(SEMVER-MINOR)</strong> <strong>lib</strong>: add aborted() utility function (Debadree Chatterjee) <a href="https://github.com/nodejs/node/pull/46494">#46494</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/5d1a729f76"><code>5d1a729f76</code></a>] - <strong>meta</strong>: update AUTHORS (Node.js GitHub Bot) <a href="https://github.com/nodejs/node/pull/46624">#46624</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/cb9b9ad879"><code>cb9b9ad879</code></a>] - <strong>meta</strong>: move one or more collaborators to emeritus (Node.js GitHub Bot) <a href="https://github.com/nodejs/node/pull/46513">#46513</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/17b82c85d9"><code>17b82c85d9</code></a>] - <strong>meta</strong>: update AUTHORS (Node.js GitHub Bot) <a href="https://github.com/nodejs/node/pull/46504">#46504</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/bb14a2b098"><code>bb14a2b098</code></a>] - <strong>meta</strong>: move one or more collaborators to emeritus (Node.js GitHub Bot) <a href="https://github.com/nodejs/node/pull/46411">#46411</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/152a3c7d1d"><code>152a3c7d1d</code></a>] - <strong>process</strong>: print versions by sort (Himself65) <a href="https://github.com/nodejs/node/pull/46428">#46428</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/164bfe82cc"><code>164bfe82cc</code></a>] - <strong>(SEMVER-MINOR)</strong> <strong>src</strong>: add initial support for single executable applications (Darshan Sen) <a href="https://github.com/nodejs/node/pull/45038">#45038</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/f3908411fd"><code>f3908411fd</code></a>] - <strong>(SEMVER-MINOR)</strong> <strong>src</strong>: allow optional Isolate termination in node::Stop() (Shelley Vohr) <a href="https://github.com/nodejs/node/pull/46583">#46583</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/bdba600d32"><code>bdba600d32</code></a>] - <strong>src</strong>: remove icu usage from node_string.cc (Yagiz Nizipli) <a href="https://github.com/nodejs/node/pull/46548">#46548</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/31fb2e22a0"><code>31fb2e22a0</code></a>] - <strong>src</strong>: add fflush() to SnapshotData::ToFile() (Anna Henningsen) <a href="https://github.com/nodejs/node/pull/46531">#46531</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/c34bac2fed"><code>c34bac2fed</code></a>] - <strong>(SEMVER-MINOR)</strong> <strong>src</strong>: allow blobs in addition to <code>FILE*</code>s in embedder snapshot API (Anna Henningsen) <a href="https://github.com/nodejs/node/pull/46491">#46491</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/c3325bfc0d"><code>c3325bfc0d</code></a>] - <strong>src</strong>: make edge names in BaseObjects more descriptive in heap snapshots (Joyee Cheung) <a href="https://github.com/nodejs/node/pull/46492">#46492</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/3c5db8f419"><code>3c5db8f419</code></a>] - <strong>src</strong>: avoid leaking snapshot fp on error (Tobias Nießen) <a href="https://github.com/nodejs/node/pull/46497">#46497</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/1a808a4aad"><code>1a808a4aad</code></a>] - <strong>src</strong>: check return value of ftell() (Tobias Nießen) <a href="https://github.com/nodejs/node/pull/46495">#46495</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/f72f643549"><code>f72f643549</code></a>] - <strong>src</strong>: remove unused includes from main thread (Yagiz Nizipli) <a href="https://github.com/nodejs/node/pull/46471">#46471</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/60c2a863da"><code>60c2a863da</code></a>] - <strong>src</strong>: use string_view instead of std::string&amp; (Yagiz Nizipli) <a href="https://github.com/nodejs/node/pull/46471">#46471</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/f35f6d2218"><code>f35f6d2218</code></a>] - <strong>src</strong>: use simdutf utf8 to utf16 instead of icu (Yagiz Nizipli) <a href="https://github.com/nodejs/node/pull/46471">#46471</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/00b81c7afe"><code>00b81c7afe</code></a>] - <strong>src</strong>: replace icu with simdutf for char counts (Yagiz Nizipli) <a href="https://github.com/nodejs/node/pull/46472">#46472</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/683a1f8f3e"><code>683a1f8f3e</code></a>] - <strong>(SEMVER-MINOR)</strong> <strong>src</strong>: allow snapshotting from the embedder API (Anna Henningsen) <a href="https://github.com/nodejs/node/pull/45888">#45888</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/658d2f4710"><code>658d2f4710</code></a>] - <strong>(SEMVER-MINOR)</strong> <strong>src</strong>: make build_snapshot a per-Isolate option, rather than a global one (Anna Henningsen) <a href="https://github.com/nodejs/node/pull/45888">#45888</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/6801d3753c"><code>6801d3753c</code></a>] - <strong>(SEMVER-MINOR)</strong> <strong>src</strong>: add snapshot support for embedder API (Anna Henningsen) <a href="https://github.com/nodejs/node/pull/45888">#45888</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/95065c3185"><code>95065c3185</code></a>] - <strong>src</strong>: add additional utilities to crypto::SecureContext (James M Snell) <a href="https://github.com/nodejs/node/pull/45912">#45912</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/efc59d0843"><code>efc59d0843</code></a>] - <strong>src</strong>: add KeyObjectHandle::HasInstance (James M Snell) <a href="https://github.com/nodejs/node/pull/45912">#45912</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/a8a2d0e2b1"><code>a8a2d0e2b1</code></a>] - <strong>src</strong>: add GetCurrentCipherName/Version to crypto_common (James M Snell) <a href="https://github.com/nodejs/node/pull/45912">#45912</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/6cf860d3d6"><code>6cf860d3d6</code></a>] - <strong>src</strong>: back snapshot I/O with a std::vector sink (Joyee Cheung) <a href="https://github.com/nodejs/node/pull/46463">#46463</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/e77d538d32"><code>e77d538d32</code></a>] - <strong>(SEMVER-MINOR)</strong> <strong>src</strong>: allow embedder control of code generation policy (Shelley Vohr) <a href="https://github.com/nodejs/node/pull/46368">#46368</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/7756438c81"><code>7756438c81</code></a>] - <strong>stream</strong>: add trailing commas in webstream source files (Antoine du Hamel) <a href="https://github.com/nodejs/node/pull/46685">#46685</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/6b64a945c6"><code>6b64a945c6</code></a>] - <strong>stream</strong>: add trailing commas in stream source files (Antoine du Hamel) <a href="https://github.com/nodejs/node/pull/46686">#46686</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/633d3f292d"><code>633d3f292d</code></a>] - <strong>(SEMVER-MINOR)</strong> <strong>stream</strong>: add abort signal for ReadableStream and WritableStream (Debadree Chatterjee) <a href="https://github.com/nodejs/node/pull/46273">#46273</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/f91260b32a"><code>f91260b32a</code></a>] - <strong>stream</strong>: refactor to use <code>validateAbortSignal</code> (Antoine du Hamel) <a href="https://github.com/nodejs/node/pull/46520">#46520</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/6bf7388b62"><code>6bf7388b62</code></a>] - <strong>stream</strong>: allow transfer of readable byte streams (MrBBot) <a href="https://github.com/nodejs/node/pull/45955">#45955</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/c2068537fa"><code>c2068537fa</code></a>] - <strong>stream</strong>: add pipeline() for webstreams (Debadree Chatterjee) <a href="https://github.com/nodejs/node/pull/46307">#46307</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/4cf4b41c56"><code>4cf4b41c56</code></a>] - <strong>stream</strong>: add suport for abort signal in finished() for webstreams (Debadree Chatterjee) <a href="https://github.com/nodejs/node/pull/46403">#46403</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/b844a09fa5"><code>b844a09fa5</code></a>] - <strong>stream</strong>: dont access Object.prototype.type during TransformStream init (Debadree Chatterjee) <a href="https://github.com/nodejs/node/pull/46389">#46389</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/6ad01fd7b5"><code>6ad01fd7b5</code></a>] - <strong>test</strong>: fix <code>test-net-autoselectfamily</code> for kernel without IPv6 support (Livia Medeiros) <a href="https://github.com/nodejs/node/pull/45856">#45856</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/2239e24306"><code>2239e24306</code></a>] - <strong>test</strong>: fix assertions in test-snapshot-dns-lookup* (Tobias Nießen) <a href="https://github.com/nodejs/node/pull/46618">#46618</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/c4ca98e786"><code>c4ca98e786</code></a>] - <strong>test</strong>: cover publicExponent validation in OpenSSL (Tobias Nießen) <a href="https://github.com/nodejs/node/pull/46632">#46632</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/e60d3f2b1d"><code>e60d3f2b1d</code></a>] - <strong>test</strong>: add WPTRunner support for variants and generating WPT reports (Filip Skokan) <a href="https://github.com/nodejs/node/pull/46498">#46498</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/217f2f6e2a"><code>217f2f6e2a</code></a>] - <strong>test</strong>: add trailing commas in <code>test/pummel</code> (Antoine du Hamel) <a href="https://github.com/nodejs/node/pull/46610">#46610</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/641e1771c8"><code>641e1771c8</code></a>] - <strong>test</strong>: enable api-invalid-label.any.js in encoding WPTs (Filip Skokan) <a href="https://github.com/nodejs/node/pull/46506">#46506</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/89aa161173"><code>89aa161173</code></a>] - <strong>test</strong>: fix tap parser fails if a test logs a number (Pulkit Gupta) <a href="https://github.com/nodejs/node/pull/46056">#46056</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/faba8d4a30"><code>faba8d4a30</code></a>] - <strong>test</strong>: add trailing commas in <code>test/js-native-api</code> (Antoine du Hamel) <a href="https://github.com/nodejs/node/pull/46385">#46385</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/d556ccdd26"><code>d556ccdd26</code></a>] - <strong>test</strong>: make more crypto tests work with BoringSSL (Shelley Vohr) <a href="https://github.com/nodejs/node/pull/46429">#46429</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/c7f29b24a6"><code>c7f29b24a6</code></a>] - <strong>test</strong>: add trailing commas in <code>test/known_issues</code> (Antoine du Hamel) <a href="https://github.com/nodejs/node/pull/46408">#46408</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/a66e7ca6c5"><code>a66e7ca6c5</code></a>] - <strong>test</strong>: add trailing commas in <code>test/internet</code> (Antoine du Hamel) <a href="https://github.com/nodejs/node/pull/46407">#46407</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/0f75633086"><code>0f75633086</code></a>] - <strong>test,crypto</strong>: update WebCryptoAPI WPT (Filip Skokan) <a href="https://github.com/nodejs/node/pull/46575">#46575</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/ddf5002782"><code>ddf5002782</code></a>] - <strong>test_runner</strong>: parse non-ascii character correctly (Mert Can Altın) <a href="https://github.com/nodejs/node/pull/45736">#45736</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/5b748114d2"><code>5b748114d2</code></a>] - <strong>test_runner</strong>: allow nesting test within describe (Moshe Atlow) <a href="https://github.com/nodejs/node/pull/46544">#46544</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/c526f9f70a"><code>c526f9f70a</code></a>] - <strong>test_runner</strong>: fix missing test diagnostics (Moshe Atlow) <a href="https://github.com/nodejs/node/pull/46450">#46450</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/b31aabb101"><code>b31aabb101</code></a>] - <strong>test_runner</strong>: top-level diagnostics not ommited when running with --test (Pulkit Gupta) <a href="https://github.com/nodejs/node/pull/46441">#46441</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/6119289251"><code>6119289251</code></a>] - <strong>test_runner</strong>: add initial code coverage support (Colin Ihrig) <a href="https://github.com/nodejs/node/pull/46017">#46017</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/6f24f0621e"><code>6f24f0621e</code></a>] - <strong>timers</strong>: cleanup no-longer relevant TODOs in timers/promises (James M Snell) <a href="https://github.com/nodejs/node/pull/46499">#46499</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/1cd22e7d19"><code>1cd22e7d19</code></a>] - <strong>tools</strong>: fix bug in <code>prefer-primordials</code> lint rule (Antoine du Hamel) <a href="https://github.com/nodejs/node/pull/46659">#46659</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/87df34ac28"><code>87df34ac28</code></a>] - <strong>tools</strong>: fix update-ada script (Yagiz Nizipli) <a href="https://github.com/nodejs/node/pull/46550">#46550</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/f62b58a623"><code>f62b58a623</code></a>] - <strong>tools</strong>: add a daily wpt.fyi synchronized report upload (Filip Skokan) <a href="https://github.com/nodejs/node/pull/46498">#46498</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/803f00aa32"><code>803f00aa32</code></a>] - <strong>tools</strong>: update eslint to 8.34.0 (Node.js GitHub Bot) <a href="https://github.com/nodejs/node/pull/46625">#46625</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/f87216bdb2"><code>f87216bdb2</code></a>] - <strong>tools</strong>: update lint-md-dependencies to rollup@3.15.0 to-vfile@7.2.4 (Node.js GitHub Bot) <a href="https://github.com/nodejs/node/pull/46623">#46623</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/8ee9e48560"><code>8ee9e48560</code></a>] - <strong>tools</strong>: update doc to remark-html@15.0.2 to-vfile@7.2.4 (Node.js GitHub Bot) <a href="https://github.com/nodejs/node/pull/46622">#46622</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/148c5d9239"><code>148c5d9239</code></a>] - <strong>tools</strong>: update lint-md-dependencies to rollup@3.13.0 vfile-reporter@7.0.5 (Node.js GitHub Bot) <a href="https://github.com/nodejs/node/pull/46503">#46503</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/51c6c61a58"><code>51c6c61a58</code></a>] - <strong>tools</strong>: update ESLint custom rules to not use the deprecated format (Antoine du Hamel) <a href="https://github.com/nodejs/node/pull/46460">#46460</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/a51fe3c663"><code>a51fe3c663</code></a>] - <strong>url</strong>: replace url-parser with ada (Yagiz Nizipli) <a href="https://github.com/nodejs/node/pull/46410">#46410</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/129c9e7180"><code>129c9e7180</code></a>] - <strong>url</strong>: remove unused <code>URL::ToFilePath()</code> (Yagiz Nizipli) <a href="https://github.com/nodejs/node/pull/46487">#46487</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/9a604d67c3"><code>9a604d67c3</code></a>] - <strong>url</strong>: remove unused <code>URL::toObject</code> (Yagiz Nizipli) <a href="https://github.com/nodejs/node/pull/46486">#46486</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/d6fbebda54"><code>d6fbebda54</code></a>] - <strong>url</strong>: remove unused <code>setURLConstructor</code> function (Yagiz Nizipli) <a href="https://github.com/nodejs/node/pull/46485">#46485</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/17b3ee33c2"><code>17b3ee33c2</code></a>] - <strong>vm</strong>: properly support symbols on globals (Nicolas DUBIEN) <a href="https://github.com/nodejs/node/pull/46458">#46458</a></li>\n</ul>'}], 
'summary': '<h3>Notable Changes</h3>\n<ul>\n<li>[<a href="https://github.com/nodejs/node/commit/60a612607e"><code>60a612607e</code></a>] - <strong>deps</strong>: upgrade npm to 9.5.0 (npm team) <a href="https://github.com/nodejs/node/pull/46673">#46673</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/7d6c27eab1"><code>7d6c27eab1</code></a>] - <strong>deps</strong>: add ada as a dependency (Yagiz Nizipli) <a href="https://github.com/nodejs/node/pull/46410">#46410</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/a79a8bf85a"><code>a79a8bf85a</code></a>] - <strong>doc</strong>: add debadree25 to collaborators (Debadree Chatterjee) <a href="https://github.com/nodejs/node/pull/46716">#46716</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/0c2c322ee6"><code>0c2c322ee6</code></a>] - <strong>doc</strong>: add deokjinkim to collaborators (Deokjin Kim) <a href="https://github.com/nodejs/node/pull/46444">#46444</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/9b23309f53"><code>9b23309f53</code></a>] - <strong>doc,lib,src,test</strong>: rename --test-coverage (Colin Ihrig) <a href="https://github.com/nodejs/node/pull/46017">#46017</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/8590eb4830"><code>8590eb4830</code></a>] - <strong>(SEMVER-MINOR)</strong> <strong>lib</strong>: add aborted() utility function (Debadree Chatterjee) <a href="https://github.com/nodejs/node/pull/46494">#46494</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/164bfe82cc"><code>164bfe82cc</code></a>] - <strong>(SEMVER-MINOR)</strong> <strong>src</strong>: add initial support for single executable applications (Darshan Sen) <a href="https://github.com/nodejs/node/pull/45038">#45038</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/f3908411fd"><code>f3908411fd</code></a>] - <strong>(SEMVER-MINOR)</strong> <strong>src</strong>: allow optional Isolate termination in node::Stop() (Shelley Vohr) <a href="https://github.com/nodejs/node/pull/46583">#46583</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/c34bac2fed"><code>c34bac2fed</code></a>] - <strong>(SEMVER-MINOR)</strong> <strong>src</strong>: allow blobs in addition to <code>FILE*</code>s in embedder snapshot API (Anna Henningsen) <a href="https://github.com/nodejs/node/pull/46491">#46491</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/683a1f8f3e"><code>683a1f8f3e</code></a>] - <strong>(SEMVER-MINOR)</strong> <strong>src</strong>: allow snapshotting from the embedder API (Anna Henningsen) <a href="https://github.com/nodejs/node/pull/45888">#45888</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/658d2f4710"><code>658d2f4710</code></a>] - <strong>(SEMVER-MINOR)</strong> <strong>src</strong>: make build_snapshot a per-Isolate option, rather than a global one (Anna Henningsen) <a href="https://github.com/nodejs/node/pull/45888">#45888</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/6801d3753c"><code>6801d3753c</code></a>] - <strong>(SEMVER-MINOR)</strong> <strong>src</strong>: add snapshot support for embedder API (Anna Henningsen) <a href="https://github.com/nodejs/node/pull/45888">#45888</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/e77d538d32"><code>e77d538d32</code></a>] - <strong>(SEMVER-MINOR)</strong> <strong>src</strong>: allow embedder control of code generation policy (Shelley Vohr) <a href="https://github.com/nodejs/node/pull/46368">#46368</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/633d3f292d"><code>633d3f292d</code></a>] - <strong>(SEMVER-MINOR)</strong> <strong>stream</strong>: add abort signal for ReadableStream and WritableStream (Debadree Chatterjee) <a href="https://github.com/nodejs/node/pull/46273">#46273</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/6119289251"><code>6119289251</code></a>] - <strong>test_runner</strong>: add initial code coverage support (Colin Ihrig) <a href="https://github.com/nodejs/node/pull/46017">#46017</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/a51fe3c663"><code>a51fe3c663</code></a>] - <strong>url</strong>: replace url-parser with ada (Yagiz Nizipli) <a href="https://github.com/nodejs/node/pull/46410">#46410</a></li>\n</ul>\n<h3>Commits</h3>\n<ul>\n<li>[<a href="https://github.com/nodejs/node/commit/731a7ae9da"><code>731a7ae9da</code></a>] - <strong>async_hooks</strong>: add async local storage propagation benchmarks (Chengzhong Wu) <a href="https://github.com/nodejs/node/pull/46414">#46414</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/05ad792a07"><code>05ad792a07</code></a>] - <strong>async_hooks</strong>: remove experimental onPropagate option (James M Snell) <a href="https://github.com/nodejs/node/pull/46386">#46386</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/6b21170b10"><code>6b21170b10</code></a>] - <strong>benchmark</strong>: add trailing commas in <code>benchmark/path</code> (Antoine du Hamel) <a href="https://github.com/nodejs/node/pull/46628">#46628</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/4b89ec409f"><code>4b89ec409f</code></a>] - <strong>benchmark</strong>: add trailing commas in <code>benchmark/http</code> (Antoine du Hamel) <a href="https://github.com/nodejs/node/pull/46609">#46609</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/ff95eb7386"><code>ff95eb7386</code></a>] - <strong>benchmark</strong>: add trailing commas in <code>benchmark/crypto</code> (Antoine du Hamel) <a href="https://github.com/nodejs/node/pull/46553">#46553</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/638d9b8d4b"><code>638d9b8d4b</code></a>] - <strong>benchmark</strong>: add trailing commas in <code>benchmark/url</code> (Antoine du Hamel) <a href="https://github.com/nodejs/node/pull/46551">#46551</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/7524871a9b"><code>7524871a9b</code></a>] - <strong>benchmark</strong>: add trailing commas in <code>benchmark/http2</code> (Antoine du Hamel) <a href="https://github.com/nodejs/node/pull/46552">#46552</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/9d9b3f856f"><code>9d9b3f856f</code></a>] - <strong>benchmark</strong>: add trailing commas in <code>benchmark/process</code> (Antoine du Hamel) <a href="https://github.com/nodejs/node/pull/46481">#46481</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/6c69ad6d43"><code>6c69ad6d43</code></a>] - <strong>benchmark</strong>: add trailing commas in <code>benchmark/misc</code> (Antoine du Hamel) <a href="https://github.com/nodejs/node/pull/46474">#46474</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/7f8b292bee"><code>7f8b292bee</code></a>] - <strong>benchmark</strong>: add trailing commas in <code>benchmark/buffers</code> (Antoine du Hamel) <a href="https://github.com/nodejs/node/pull/46473">#46473</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/897e3c2782"><code>897e3c2782</code></a>] - <strong>benchmark</strong>: add trailing commas in <code>benchmark/module</code> (Antoine du Hamel) <a href="https://github.com/nodejs/node/pull/46461">#46461</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/7760d40c04"><code>7760d40c04</code></a>] - <strong>benchmark</strong>: add trailing commas in <code>benchmark/net</code> (Antoine du Hamel) <a href="https://github.com/nodejs/node/pull/46439">#46439</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/8b88d605ca"><code>8b88d605ca</code></a>] - <strong>benchmark</strong>: add trailing commas in <code>benchmark/util</code> (Antoine du Hamel) <a href="https://github.com/nodejs/node/pull/46438">#46438</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/2c8c9f978d"><code>2c8c9f978d</code></a>] - <strong>benchmark</strong>: add trailing commas in <code>benchmark/async_hooks</code> (Antoine du Hamel) <a href="https://github.com/nodejs/node/pull/46424">#46424</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/b364b9bd60"><code>b364b9bd60</code></a>] - <strong>benchmark</strong>: add trailing commas in <code>benchmark/fs</code> (Antoine du Hamel) <a href="https://github.com/nodejs/node/pull/46426">#46426</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/e15ddba7e7"><code>e15ddba7e7</code></a>] - <strong>build</strong>: add GitHub Action for coverage with --without-intl (Rich Trott) <a href="https://github.com/nodejs/node/pull/37954">#37954</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/c781a48097"><code>c781a48097</code></a>] - <strong>build</strong>: do not disable inspector when intl is disabled (Rich Trott) <a href="https://github.com/nodejs/node/pull/37954">#37954</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/b4deb2fcd5"><code>b4deb2fcd5</code></a>] - <strong>crypto</strong>: don\'t assume FIPS is disabled by default (Michael Dawson) <a href="https://github.com/nodejs/node/pull/46532">#46532</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/60a612607e"><code>60a612607e</code></a>] - <strong>deps</strong>: upgrade npm to 9.5.0 (npm team) <a href="https://github.com/nodejs/node/pull/46673">#46673</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/6c997035fc"><code>6c997035fc</code></a>] - <strong>deps</strong>: update corepack to 0.16.0 (Node.js GitHub Bot) <a href="https://github.com/nodejs/node/pull/46710">#46710</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/2ed3875eee"><code>2ed3875eee</code></a>] - <strong>deps</strong>: update undici to 5.20.0 (Node.js GitHub Bot) <a href="https://github.com/nodejs/node/pull/46711">#46711</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/20cb13bf7f"><code>20cb13bf7f</code></a>] - <strong>deps</strong>: update ada to v1.0.1 (Yagiz Nizipli) <a href="https://github.com/nodejs/node/pull/46550">#46550</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/c0983cfc06"><code>c0983cfc06</code></a>] - <strong>deps</strong>: copy <code>postject-api.h</code> and <code>LICENSE</code> to the <code>deps</code> folder (Darshan Sen) <a href="https://github.com/nodejs/node/pull/46582">#46582</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/7d6c27eab1"><code>7d6c27eab1</code></a>] - <strong>deps</strong>: add ada as a dependency (Yagiz Nizipli) <a href="https://github.com/nodejs/node/pull/46410">#46410</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/7e7e2d037b"><code>7e7e2d037b</code></a>] - <strong>deps</strong>: update c-ares to 1.19.0 (Michaël Zasso) <a href="https://github.com/nodejs/node/pull/46415">#46415</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/a79a8bf85a"><code>a79a8bf85a</code></a>] - <strong>doc</strong>: add debadree25 to collaborators (Debadree Chatterjee) <a href="https://github.com/nodejs/node/pull/46716">#46716</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/6a8b04d709"><code>6a8b04d709</code></a>] - <strong>doc</strong>: move bcoe to emeriti (Benjamin Coe) <a href="https://github.com/nodejs/node/pull/46703">#46703</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/a0a6ee0f54"><code>a0a6ee0f54</code></a>] - <strong>doc</strong>: add response.strictContentLength to documentation (Marco Ippolito) <a href="https://github.com/nodejs/node/pull/46627">#46627</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/ffdd64dce3"><code>ffdd64dce3</code></a>] - <strong>doc</strong>: remove unused functions from example of <code>streamConsumers.text</code> (Deokjin Kim) <a href="https://github.com/nodejs/node/pull/46581">#46581</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/c771d66864"><code>c771d66864</code></a>] - <strong>doc</strong>: fix test runner examples (Richie McColl) <a href="https://github.com/nodejs/node/pull/46565">#46565</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/375bb22df9"><code>375bb22df9</code></a>] - <strong>doc</strong>: update test concurrency description / default values (richiemccoll) <a href="https://github.com/nodejs/node/pull/46457">#46457</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/a7beac04ba"><code>a7beac04ba</code></a>] - <strong>doc</strong>: enrich test command with executable (Tony Gorez) <a href="https://github.com/nodejs/node/pull/44347">#44347</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/aef57cd290"><code>aef57cd290</code></a>] - <strong>doc</strong>: fix wrong location of <code>requestTimeout</code>\'s default value (Deokjin Kim) <a href="https://github.com/nodejs/node/pull/46423">#46423</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/0c2c322ee6"><code>0c2c322ee6</code></a>] - <strong>doc</strong>: add deokjinkim to collaborators (Deokjin Kim) <a href="https://github.com/nodejs/node/pull/46444">#46444</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/31d3e3c486"><code>31d3e3c486</code></a>] - <strong>doc</strong>: fix -C flag usage (三咲智子 Kevin Deng) <a href="https://github.com/nodejs/node/pull/46388">#46388</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/905a6756a3"><code>905a6756a3</code></a>] - <strong>doc</strong>: add note about major release rotation (Rafael Gonzaga) <a href="https://github.com/nodejs/node/pull/46436">#46436</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/33a98c42fa"><code>33a98c42fa</code></a>] - <strong>doc</strong>: update threat model based on discussions (Michael Dawson) <a href="https://github.com/nodejs/node/pull/46373">#46373</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/9b23309f53"><code>9b23309f53</code></a>] - <strong>doc,lib,src,test</strong>: rename --test-coverage (Colin Ihrig) <a href="https://github.com/nodejs/node/pull/46017">#46017</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/f192b83800"><code>f192b83800</code></a>] - <strong>esm</strong>: misc test refactors (Geoffrey Booth) <a href="https://github.com/nodejs/node/pull/46631">#46631</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/7f2cdd36cf"><code>7f2cdd36cf</code></a>] - <strong>http</strong>: add note about clientError event (Paolo Insogna) <a href="https://github.com/nodejs/node/pull/46584">#46584</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/d8c527f24f"><code>d8c527f24f</code></a>] - <strong>http</strong>: use v8::Array::New() with a prebuilt vector (Joyee Cheung) <a href="https://github.com/nodejs/node/pull/46447">#46447</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/fa600fe003"><code>fa600fe003</code></a>] - <strong>lib</strong>: add trailing commas in <code>internal/process</code> (Antoine du Hamel) <a href="https://github.com/nodejs/node/pull/46687">#46687</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/4aebee63f0"><code>4aebee63f0</code></a>] - <strong>lib</strong>: do not crash using workers with disabled shared array buffers (Ruben Bridgewater) <a href="https://github.com/nodejs/node/pull/41023">#41023</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/a740908588"><code>a740908588</code></a>] - <strong>lib</strong>: delete module findPath unused params (sinkhaha) <a href="https://github.com/nodejs/node/pull/45371">#45371</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/8b46c763d9"><code>8b46c763d9</code></a>] - <strong>lib</strong>: enforce use of trailing commas in more files (Antoine du Hamel) <a href="https://github.com/nodejs/node/pull/46655">#46655</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/aae0020e27"><code>aae0020e27</code></a>] - <strong>lib</strong>: enforce use of trailing commas for functions (Antoine du Hamel) <a href="https://github.com/nodejs/node/pull/46629">#46629</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/da9ebaf138"><code>da9ebaf138</code></a>] - <strong>lib</strong>: predeclare Event.isTrusted prop descriptor (Santiago Gimeno) <a href="https://github.com/nodejs/node/pull/46527">#46527</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/35570e970e"><code>35570e970e</code></a>] - <strong>lib</strong>: tighten <code>AbortSignal.prototype.throwIfAborted</code> implementation (Antoine du Hamel) <a href="https://github.com/nodejs/node/pull/46521">#46521</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/8590eb4830"><code>8590eb4830</code></a>] - <strong>(SEMVER-MINOR)</strong> <strong>lib</strong>: add aborted() utility function (Debadree Chatterjee) <a href="https://github.com/nodejs/node/pull/46494">#46494</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/5d1a729f76"><code>5d1a729f76</code></a>] - <strong>meta</strong>: update AUTHORS (Node.js GitHub Bot) <a href="https://github.com/nodejs/node/pull/46624">#46624</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/cb9b9ad879"><code>cb9b9ad879</code></a>] - <strong>meta</strong>: move one or more collaborators to emeritus (Node.js GitHub Bot) <a href="https://github.com/nodejs/node/pull/46513">#46513</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/17b82c85d9"><code>17b82c85d9</code></a>] - <strong>meta</strong>: update AUTHORS (Node.js GitHub Bot) <a href="https://github.com/nodejs/node/pull/46504">#46504</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/bb14a2b098"><code>bb14a2b098</code></a>] - <strong>meta</strong>: move one or more collaborators to emeritus (Node.js GitHub Bot) <a href="https://github.com/nodejs/node/pull/46411">#46411</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/152a3c7d1d"><code>152a3c7d1d</code></a>] - <strong>process</strong>: print versions by sort (Himself65) <a href="https://github.com/nodejs/node/pull/46428">#46428</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/164bfe82cc"><code>164bfe82cc</code></a>] - <strong>(SEMVER-MINOR)</strong> <strong>src</strong>: add initial support for single executable applications (Darshan Sen) <a href="https://github.com/nodejs/node/pull/45038">#45038</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/f3908411fd"><code>f3908411fd</code></a>] - <strong>(SEMVER-MINOR)</strong> <strong>src</strong>: allow optional Isolate termination in node::Stop() (Shelley Vohr) <a href="https://github.com/nodejs/node/pull/46583">#46583</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/bdba600d32"><code>bdba600d32</code></a>] - <strong>src</strong>: remove icu usage from node_string.cc (Yagiz Nizipli) <a href="https://github.com/nodejs/node/pull/46548">#46548</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/31fb2e22a0"><code>31fb2e22a0</code></a>] - <strong>src</strong>: add fflush() to SnapshotData::ToFile() (Anna Henningsen) <a href="https://github.com/nodejs/node/pull/46531">#46531</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/c34bac2fed"><code>c34bac2fed</code></a>] - <strong>(SEMVER-MINOR)</strong> <strong>src</strong>: allow blobs in addition to <code>FILE*</code>s in embedder snapshot API (Anna Henningsen) <a href="https://github.com/nodejs/node/pull/46491">#46491</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/c3325bfc0d"><code>c3325bfc0d</code></a>] - <strong>src</strong>: make edge names in BaseObjects more descriptive in heap snapshots (Joyee Cheung) <a href="https://github.com/nodejs/node/pull/46492">#46492</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/3c5db8f419"><code>3c5db8f419</code></a>] - <strong>src</strong>: avoid leaking snapshot fp on error (Tobias Nießen) <a href="https://github.com/nodejs/node/pull/46497">#46497</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/1a808a4aad"><code>1a808a4aad</code></a>] - <strong>src</strong>: check return value of ftell() (Tobias Nießen) <a href="https://github.com/nodejs/node/pull/46495">#46495</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/f72f643549"><code>f72f643549</code></a>] - <strong>src</strong>: remove unused includes from main thread (Yagiz Nizipli) <a href="https://github.com/nodejs/node/pull/46471">#46471</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/60c2a863da"><code>60c2a863da</code></a>] - <strong>src</strong>: use string_view instead of std::string&amp; (Yagiz Nizipli) <a href="https://github.com/nodejs/node/pull/46471">#46471</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/f35f6d2218"><code>f35f6d2218</code></a>] - <strong>src</strong>: use simdutf utf8 to utf16 instead of icu (Yagiz Nizipli) <a href="https://github.com/nodejs/node/pull/46471">#46471</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/00b81c7afe"><code>00b81c7afe</code></a>] - <strong>src</strong>: replace icu with simdutf for char counts (Yagiz Nizipli) <a href="https://github.com/nodejs/node/pull/46472">#46472</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/683a1f8f3e"><code>683a1f8f3e</code></a>] - <strong>(SEMVER-MINOR)</strong> <strong>src</strong>: allow snapshotting from the embedder API (Anna Henningsen) <a href="https://github.com/nodejs/node/pull/45888">#45888</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/658d2f4710"><code>658d2f4710</code></a>] - <strong>(SEMVER-MINOR)</strong> <strong>src</strong>: make build_snapshot a per-Isolate option, rather than a global one (Anna Henningsen) <a href="https://github.com/nodejs/node/pull/45888">#45888</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/6801d3753c"><code>6801d3753c</code></a>] - <strong>(SEMVER-MINOR)</strong> <strong>src</strong>: add snapshot support for embedder API (Anna Henningsen) <a href="https://github.com/nodejs/node/pull/45888">#45888</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/95065c3185"><code>95065c3185</code></a>] - <strong>src</strong>: add additional utilities to crypto::SecureContext (James M Snell) <a href="https://github.com/nodejs/node/pull/45912">#45912</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/efc59d0843"><code>efc59d0843</code></a>] - <strong>src</strong>: add KeyObjectHandle::HasInstance (James M Snell) <a href="https://github.com/nodejs/node/pull/45912">#45912</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/a8a2d0e2b1"><code>a8a2d0e2b1</code></a>] - <strong>src</strong>: add GetCurrentCipherName/Version to crypto_common (James M Snell) <a href="https://github.com/nodejs/node/pull/45912">#45912</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/6cf860d3d6"><code>6cf860d3d6</code></a>] - <strong>src</strong>: back snapshot I/O with a std::vector sink (Joyee Cheung) <a href="https://github.com/nodejs/node/pull/46463">#46463</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/e77d538d32"><code>e77d538d32</code></a>] - <strong>(SEMVER-MINOR)</strong> <strong>src</strong>: allow embedder control of code generation policy (Shelley Vohr) <a href="https://github.com/nodejs/node/pull/46368">#46368</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/7756438c81"><code>7756438c81</code></a>] - <strong>stream</strong>: add trailing commas in webstream source files (Antoine du Hamel) <a href="https://github.com/nodejs/node/pull/46685">#46685</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/6b64a945c6"><code>6b64a945c6</code></a>] - <strong>stream</strong>: add trailing commas in stream source files (Antoine du Hamel) <a href="https://github.com/nodejs/node/pull/46686">#46686</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/633d3f292d"><code>633d3f292d</code></a>] - <strong>(SEMVER-MINOR)</strong> <strong>stream</strong>: add abort signal for ReadableStream and WritableStream (Debadree Chatterjee) <a href="https://github.com/nodejs/node/pull/46273">#46273</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/f91260b32a"><code>f91260b32a</code></a>] - <strong>stream</strong>: refactor to use <code>validateAbortSignal</code> (Antoine du Hamel) <a href="https://github.com/nodejs/node/pull/46520">#46520</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/6bf7388b62"><code>6bf7388b62</code></a>] - <strong>stream</strong>: allow transfer of readable byte streams (MrBBot) <a href="https://github.com/nodejs/node/pull/45955">#45955</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/c2068537fa"><code>c2068537fa</code></a>] - <strong>stream</strong>: add pipeline() for webstreams (Debadree Chatterjee) <a href="https://github.com/nodejs/node/pull/46307">#46307</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/4cf4b41c56"><code>4cf4b41c56</code></a>] - <strong>stream</strong>: add suport for abort signal in finished() for webstreams (Debadree Chatterjee) <a href="https://github.com/nodejs/node/pull/46403">#46403</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/b844a09fa5"><code>b844a09fa5</code></a>] - <strong>stream</strong>: dont access Object.prototype.type during TransformStream init (Debadree Chatterjee) <a href="https://github.com/nodejs/node/pull/46389">#46389</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/6ad01fd7b5"><code>6ad01fd7b5</code></a>] - <strong>test</strong>: fix <code>test-net-autoselectfamily</code> for kernel without IPv6 support (Livia Medeiros) <a href="https://github.com/nodejs/node/pull/45856">#45856</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/2239e24306"><code>2239e24306</code></a>] - <strong>test</strong>: fix assertions in test-snapshot-dns-lookup* (Tobias Nießen) <a href="https://github.com/nodejs/node/pull/46618">#46618</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/c4ca98e786"><code>c4ca98e786</code></a>] - <strong>test</strong>: cover publicExponent validation in OpenSSL (Tobias Nießen) <a href="https://github.com/nodejs/node/pull/46632">#46632</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/e60d3f2b1d"><code>e60d3f2b1d</code></a>] - <strong>test</strong>: add WPTRunner support for variants and generating WPT reports (Filip Skokan) <a href="https://github.com/nodejs/node/pull/46498">#46498</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/217f2f6e2a"><code>217f2f6e2a</code></a>] - <strong>test</strong>: add trailing commas in <code>test/pummel</code> (Antoine du Hamel) <a href="https://github.com/nodejs/node/pull/46610">#46610</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/641e1771c8"><code>641e1771c8</code></a>] - <strong>test</strong>: enable api-invalid-label.any.js in encoding WPTs (Filip Skokan) <a href="https://github.com/nodejs/node/pull/46506">#46506</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/89aa161173"><code>89aa161173</code></a>] - <strong>test</strong>: fix tap parser fails if a test logs a number (Pulkit Gupta) <a href="https://github.com/nodejs/node/pull/46056">#46056</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/faba8d4a30"><code>faba8d4a30</code></a>] - <strong>test</strong>: add trailing commas in <code>test/js-native-api</code> (Antoine du Hamel) <a href="https://github.com/nodejs/node/pull/46385">#46385</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/d556ccdd26"><code>d556ccdd26</code></a>] - <strong>test</strong>: make more crypto tests work with BoringSSL (Shelley Vohr) <a href="https://github.com/nodejs/node/pull/46429">#46429</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/c7f29b24a6"><code>c7f29b24a6</code></a>] - <strong>test</strong>: add trailing commas in <code>test/known_issues</code> (Antoine du Hamel) <a href="https://github.com/nodejs/node/pull/46408">#46408</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/a66e7ca6c5"><code>a66e7ca6c5</code></a>] - <strong>test</strong>: add trailing commas in <code>test/internet</code> (Antoine du Hamel) <a href="https://github.com/nodejs/node/pull/46407">#46407</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/0f75633086"><code>0f75633086</code></a>] - <strong>test,crypto</strong>: update WebCryptoAPI WPT (Filip Skokan) <a href="https://github.com/nodejs/node/pull/46575">#46575</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/ddf5002782"><code>ddf5002782</code></a>] - <strong>test_runner</strong>: parse non-ascii character correctly (Mert Can Altın) <a href="https://github.com/nodejs/node/pull/45736">#45736</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/5b748114d2"><code>5b748114d2</code></a>] - <strong>test_runner</strong>: allow nesting test within describe (Moshe Atlow) <a href="https://github.com/nodejs/node/pull/46544">#46544</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/c526f9f70a"><code>c526f9f70a</code></a>] - <strong>test_runner</strong>: fix missing test diagnostics (Moshe Atlow) <a href="https://github.com/nodejs/node/pull/46450">#46450</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/b31aabb101"><code>b31aabb101</code></a>] - <strong>test_runner</strong>: top-level diagnostics not ommited when running with --test (Pulkit Gupta) <a href="https://github.com/nodejs/node/pull/46441">#46441</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/6119289251"><code>6119289251</code></a>] - <strong>test_runner</strong>: add initial code coverage support (Colin Ihrig) <a href="https://github.com/nodejs/node/pull/46017">#46017</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/6f24f0621e"><code>6f24f0621e</code></a>] - <strong>timers</strong>: cleanup no-longer relevant TODOs in timers/promises (James M Snell) <a href="https://github.com/nodejs/node/pull/46499">#46499</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/1cd22e7d19"><code>1cd22e7d19</code></a>] - <strong>tools</strong>: fix bug in <code>prefer-primordials</code> lint rule (Antoine du Hamel) <a href="https://github.com/nodejs/node/pull/46659">#46659</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/87df34ac28"><code>87df34ac28</code></a>] - <strong>tools</strong>: fix update-ada script (Yagiz Nizipli) <a href="https://github.com/nodejs/node/pull/46550">#46550</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/f62b58a623"><code>f62b58a623</code></a>] - <strong>tools</strong>: add a daily wpt.fyi synchronized report upload (Filip Skokan) <a href="https://github.com/nodejs/node/pull/46498">#46498</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/803f00aa32"><code>803f00aa32</code></a>] - <strong>tools</strong>: update eslint to 8.34.0 (Node.js GitHub Bot) <a href="https://github.com/nodejs/node/pull/46625">#46625</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/f87216bdb2"><code>f87216bdb2</code></a>] - <strong>tools</strong>: update lint-md-dependencies to rollup@3.15.0 to-vfile@7.2.4 (Node.js GitHub Bot) <a href="https://github.com/nodejs/node/pull/46623">#46623</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/8ee9e48560"><code>8ee9e48560</code></a>] - <strong>tools</strong>: update doc to remark-html@15.0.2 to-vfile@7.2.4 (Node.js GitHub Bot) <a href="https://github.com/nodejs/node/pull/46622">#46622</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/148c5d9239"><code>148c5d9239</code></a>] - <strong>tools</strong>: update lint-md-dependencies to rollup@3.13.0 vfile-reporter@7.0.5 (Node.js GitHub Bot) <a href="https://github.com/nodejs/node/pull/46503">#46503</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/51c6c61a58"><code>51c6c61a58</code></a>] - <strong>tools</strong>: update ESLint custom rules to not use the deprecated format (Antoine du Hamel) <a href="https://github.com/nodejs/node/pull/46460">#46460</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/a51fe3c663"><code>a51fe3c663</code></a>] - <strong>url</strong>: replace url-parser with ada (Yagiz Nizipli) <a href="https://github.com/nodejs/node/pull/46410">#46410</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/129c9e7180"><code>129c9e7180</code></a>] - <strong>url</strong>: remove unused <code>URL::ToFilePath()</code> (Yagiz Nizipli) <a href="https://github.com/nodejs/node/pull/46487">#46487</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/9a604d67c3"><code>9a604d67c3</code></a>] - <strong>url</strong>: remove unused <code>URL::toObject</code> (Yagiz Nizipli) <a href="https://github.com/nodejs/node/pull/46486">#46486</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/d6fbebda54"><code>d6fbebda54</code></a>] - <strong>url</strong>: remove unused <code>setURLConstructor</code> function (Yagiz Nizipli) <a href="https://github.com/nodejs/node/pull/46485">#46485</a></li>\n<li>[<a href="https://github.com/nodejs/node/commit/17b3ee33c2"><code>17b3ee33c2</code></a>] - <strong>vm</strong>: properly support symbols on globals (Nicolas DUBIEN) <a href="https://github.com/nodejs/node/pull/46458">#46458</a></li>\n</ul>', 
'authors': [{'name': 'MylesBorins'}], 
'author_detail': {'name': 'MylesBorins'}, 
'author': 'MylesBorins', 
'media_thumbnail': [
		{'height': '30', 'width': '30', 'url': 'https://avatars.githubusercontent.com/u/498775?s=60&v=4'}
], 
'href': ''
}
```

## Sonar Scanner Cli Feed

URL

```bash
https://github.com/SonarSource/sonar-scanner-cli/releases.atom
```

Key components

```bash
'title': '4.8.0.2856', 
'updated': '2023-02-21T18:18:33Z',

'link': 'https://github.com/SonarSource/sonar-scanner-cli/releases/tag/4.8.0.2856',
```

Constraint

- Summary param does not provide information about the version update
- Cannot filter pre-releases as there is no identifier within entry to distinguish release types
    - Requires Gitlab API

raw sample rss entry

```bash
{
'id': 'tag:github.com,2008:Repository/45852702/4.8.0.2856', 
'guidislink': True, 
'link': 'https://github.com/SonarSource/sonar-scanner-cli/releases/tag/4.8.0.2856', 
'updated': '2022-12-22T16:25:41Z', 
'updated_parsed': 
		time.struct_time(
				tm_year=2022, 
				tm_mon=12, 
				tm_mday=22, 
				tm_hour=16, 
				tm_min=25, 
				tm_sec=41, 
				tm_wday=3, 
				tm_yday=356, 
				tm_isdst=0), 
'links': [
		{'rel': 'alternate', 'type': 'text/html', 
			'href': 'https://github.com/SonarSource/sonar-scanner-cli/releases/tag/4.8.0.2856'}
], 
'title': '4.8.0.2856', 
'title_detail': 
		{'type': 'text/plain', 
			'language': 'en-US', 
			'base': 'https://github.com/SonarSource/sonar-scanner-cli/releases.atom', 
			'value': '4.8.0.2856'}, 
'content': [
		{'type': 'text/plain', 'language': 'en-US', 
			'base': 'https://github.com/SonarSource/sonar-scanner-cli/releases.atom', 
			'value': 'No content.'}
], 
'summary': 'No content.', 
'authors': [{'name': 'jacek-poreda-sonarsource'}], 
'author_detail': {'name': 'jacek-poreda-sonarsource'}, 
'author': 'jacek-poreda-sonarsource', 
'media_thumbnail': [
		{'height': '30', 'width': '30', 'url': 'https://avatars.githubusercontent.com/u/52388493?s=60&v=4'}
], 
'href': ''
}
```

## Sonarqube Feed

### Github

URL

```bash
https://github.com/SonarSource/sonarqube/releases.atom
```

Key components

```bash
'title': '9.9.0.65466', 
'updated': '2023-02-07T09:38:22Z', 
'summary': '<p>See details in the <a href="https://www.sonarsource.com/products/sonarqube/downloads/lts/9-9-lts/" rel="nofollow">official announcement</a>.<br />\nYou\'ll find more in the <a href="https://community.sonarsource.com/t/sonarqube-9-9-lts-released/83246" rel="nofollow">community announcement</a>, and full details in the <a href="https://sonarsource.atlassian.net/issues/?jql=project%20%3D%2010139%20AND%20fixVersion%20%3D%2013931" rel="nofollow">release notes</a>.</p>',
'link': 'https://github.com/SonarSource/sonarqube/releases/tag/9.9.0.65466'
```

Constraint

- Cannot filter pre-releases as there is no identifier within entry to distinguish release types
    - Requires Gitlab API

raw sample rss entry

```bash
{
'id': 'tag:github.com,2008:Repository/1222504/9.9.0.65466', 
'guidislink': True, 
'link': 'https://github.com/SonarSource/sonarqube/releases/tag/9.9.0.65466', 
'updated': '2023-02-07T09:38:22Z', 
'updated_parsed': 
		time.struct_time(
				tm_year=2023, 
				tm_mon=2, 
				tm_mday=7, 
				tm_hour=9, 
				tm_min=38, 
				tm_sec=22, 
				tm_wday=1, 
				tm_yday=38, 
				tm_isdst=0), 
'links': [
		{'rel': 'alternate', 'type': 'text/html', 
			'href': 'https://github.com/SonarSource/sonarqube/releases/tag/9.9.0.65466'}
], 
'title': '9.9.0.65466', 
'title_detail': 
		{'type': 'text/plain', 
			'language': 'en-US', 
			'base': 'https://github.com/SonarSource/sonarqube/releases.atom', 
			'value': '9.9.0.65466'}, 
'content': [
		{'type': 'text/html', 
			'language': 'en-US', 
			'base': 'https://github.com/SonarSource/sonarqube/releases.atom', 
			'value': '<p>See details in the <a href="https://www.sonarsource.com/products/sonarqube/downloads/lts/9-9-lts/" rel="nofollow">official announcement</a>.<br />\nYou\'ll find more in the <a href="https://community.sonarsource.com/t/sonarqube-9-9-lts-released/83246" rel="nofollow">community announcement</a>, and full details in the <a href="https://sonarsource.atlassian.net/issues/?jql=project%20%3D%2010139%20AND%20fixVersion%20%3D%2013931" rel="nofollow">release notes</a>.</p>'}
], 
'summary': '<p>See details in the <a href="https://www.sonarsource.com/products/sonarqube/downloads/lts/9-9-lts/" rel="nofollow">official announcement</a>.<br />\nYou\'ll find more in the <a href="https://community.sonarsource.com/t/sonarqube-9-9-lts-released/83246" rel="nofollow">community announcement</a>, and full details in the <a href="https://sonarsource.atlassian.net/issues/?jql=project%20%3D%2010139%20AND%20fixVersion%20%3D%2013931" rel="nofollow">release notes</a>.</p>', 
'authors': [{'name': 'alain-kermis-sonarsource'}],
'author_detail': {'name': 'alain-kermis-sonarsource'}, 
'author': 'alain-kermis-sonarsource', 
'media_thumbnail': [
		{'height': '30', 'width': '30', 'url': 'https://avatars.githubusercontent.com/u/108417558?s=60&v=4'}
], 
'href': ''
}
```

### Community Sonarsource

URL

```python
https://community.sonarsource.com/c/sq/releases/24.rss
```

Key Components

```python
'title': 'SonarQube 9.9 LTS released', 
'published': 'Tue, 07 Feb 2023 08:28:34 +0000', 
'link': 'https://community.sonarsource.com/t/sonarqube-9-9-lts-released/83246', 
'summary': '<p>Hi all,</p>\n<p>SonarSource is thrilled to announce the release of SonarQube 9.9, the new LTS! <img alt=":tada:" height="20" src="https://europe1.discourse-cdn.com/sonarsource/uploads/sonarcommunity/original/2X/e/e69717ced28a53ad899c5024deac74a0b929ddd1.png" title=":tada:" width="20" /></p>\n<p>You’ll find a summary of all the new features added since the previous LTS in the <a href="https://www.sonarsource.com/products/sonarqube/downloads/lts/9-9-lts/">official announcement</a>. You can take a look at the highlights there, see all the great features we’ve worked on since the previous LTS including faster Pull Request analysis, securing cloud native apps, enterprise-grade features for easy operability, security and management of your instance.</p>\n<p>In addition, there are a few other items to note since the last (9.8) release:</p>\n<ul>\n<li>The SonarQube server now requires Java 17. Analysis may continue to use Java 11 if necessary. (<a href="https://sonarsource.atlassian.net/browse/SONAR-17566">SONAR-17566</a>).</li>\n<li>We’ve updated the list of supported database versions. See more details in the <a href="https://docs.sonarqube.org/latest/requirements/prerequisites-and-overview/">prerequisites documentation</a>. (<a href="https://sonarsource.atlassian.net/browse/SONAR-17712">SONAR-17712</a>, <a href="https://sonarsource.atlassian.net/browse/SONAR-17713">SONAR-17713</a>, <a href="https://sonarsource.atlassian.net/browse/SONAR-17742">SONAR-17742</a>).</li>\n<li>We’ve also updated the list of supported DevOps platform versions. See more details in the documentation, such as for example in the <a href="https://docs.sonarqube.org/latest/devops-platform-integration/github-integration/">documentation for GitHub</a>. (<a href="https://sonarsource.atlassian.net/browse/SONAR-17756">SONAR-17756</a>).</li>\n<li>We’ve improved the user experience for Quality Gates to help everyone implement the <a href="https://docs.sonarqube.org/latest/user-guide/clean-as-you-code/#quality-gate">Clean as You Code methodology</a>. SonarQube helps you identify and fix Quality Gates that are not compliant with Clean as You Code. (<a href="https://sonarsource.atlassian.net/browse/SONAR-17815">SONAR-17815</a>, <a href="https://sonarsource.atlassian.net/browse/SONAR-17816">SONAR-17816</a>, <a href="https://sonarsource.atlassian.net/browse/SONAR-17818">SONAR-17818</a>)</li>\n<li>We’ve also added information in telemetry to better understand the impact of the Clean as You Code methodology. See more details in the <a href="https://docs.sonarqube.org/latest/instance-administration/telemetry/">telemetry documentation</a>. (<a href="https://sonarsource.atlassian.net/browse/SONAR-18188">SONAR-18188</a>, <a href="https://sonarsource.atlassian.net/browse/SONAR-18219">SONAR-18219</a>).</li>\n<li>We’ve made new accessibility improvements on various pages. (<a href="https://sonarsource.atlassian.net/browse/SONAR-18131">SONAR-18131</a>, <a href="https://sonarsource.atlassian.net/browse/SONAR-17845">SONAR-17845</a>).</li>\n<li>The Docker image is now available for arm64-based Apple Silicon (M1).</li>\n</ul>\n<p>You’ll find more details in the <a href="https://docs.sonarqube.org/latest/setup-and-upgrade/release-upgrade-notes/">upgrade notes</a> and full details in the <a href="https://sonarsource.atlassian.net/issues/?jql=project%20%3D%2010139%20AND%20fixVersion%20%3D%2013931">release notes</a>.</p>\n<p>If you’re upgrading across multiple versions, you should at a minimum read the upgrade notes for the intervening versions. If you’re upgrading from the previous LTS (8.9), you’ll find a consolidated version in the <a href="https://docs.sonarqube.org/9.9/setup-and-upgrade/lts-to-lts-release-upgrade-notes/">LTS to LTS upgrade notes</a>. Also don’t forget that if you run a version older than the previous LTS (8.9), you need to upgrade to 8.9.10 first, and then to 9.9 LTS.</p>\n<p>Please open new threads for any questions you have about these or other features.</p>\n<p>As usual, <a href="https://www.sonarsource.com/products/sonarqube/downloads/">downloads are available at sonarsource.com</a>. Docker images are also available on <a href="https://hub.docker.com/_/sonarqube">Docker Hub</a>.</p>\n<p>&nbsp;<br />\nVivek &amp; Chris</p>\n            <p><small>9 posts - 5 participants</small></p>\n            <p><a href="https://community.sonarsource.com/t/sonarqube-9-9-lts-released/83246">Read full topic</a></p>', 
```

raw sample rss entry

```python
{
'title': 'SonarQube 9.9 LTS released', 
'title_detail': 
		{'type': 'text/plain', 'language': None, 
		'base': 'https://community.sonarsource.com/c/sq/releases/24.rss', 
		'value': 'SonarQube 9.9 LTS released'}, 
'authors': [{'name': 'Christophe Lévis'}], 
'author': 'Christophe Lévis', 
'author_detail': {'name': 'Christophe Lévis'}, 
'tags': [{'term': 'Releases', 'scheme': None, 'label': None}], 
'summary': '<p>Hi all,</p>\n<p>SonarSource is thrilled to announce the release of SonarQube 9.9, the new LTS! <img alt=":tada:" height="20" src="https://europe1.discourse-cdn.com/sonarsource/uploads/sonarcommunity/original/2X/e/e69717ced28a53ad899c5024deac74a0b929ddd1.png" title=":tada:" width="20" /></p>\n<p>You’ll find a summary of all the new features added since the previous LTS in the <a href="https://www.sonarsource.com/products/sonarqube/downloads/lts/9-9-lts/">official announcement</a>. You can take a look at the highlights there, see all the great features we’ve worked on since the previous LTS including faster Pull Request analysis, securing cloud native apps, enterprise-grade features for easy operability, security and management of your instance.</p>\n<p>In addition, there are a few other items to note since the last (9.8) release:</p>\n<ul>\n<li>The SonarQube server now requires Java 17. Analysis may continue to use Java 11 if necessary. (<a href="https://sonarsource.atlassian.net/browse/SONAR-17566">SONAR-17566</a>).</li>\n<li>We’ve updated the list of supported database versions. See more details in the <a href="https://docs.sonarqube.org/latest/requirements/prerequisites-and-overview/">prerequisites documentation</a>. (<a href="https://sonarsource.atlassian.net/browse/SONAR-17712">SONAR-17712</a>, <a href="https://sonarsource.atlassian.net/browse/SONAR-17713">SONAR-17713</a>, <a href="https://sonarsource.atlassian.net/browse/SONAR-17742">SONAR-17742</a>).</li>\n<li>We’ve also updated the list of supported DevOps platform versions. See more details in the documentation, such as for example in the <a href="https://docs.sonarqube.org/latest/devops-platform-integration/github-integration/">documentation for GitHub</a>. (<a href="https://sonarsource.atlassian.net/browse/SONAR-17756">SONAR-17756</a>).</li>\n<li>We’ve improved the user experience for Quality Gates to help everyone implement the <a href="https://docs.sonarqube.org/latest/user-guide/clean-as-you-code/#quality-gate">Clean as You Code methodology</a>. SonarQube helps you identify and fix Quality Gates that are not compliant with Clean as You Code. (<a href="https://sonarsource.atlassian.net/browse/SONAR-17815">SONAR-17815</a>, <a href="https://sonarsource.atlassian.net/browse/SONAR-17816">SONAR-17816</a>, <a href="https://sonarsource.atlassian.net/browse/SONAR-17818">SONAR-17818</a>)</li>\n<li>We’ve also added information in telemetry to better understand the impact of the Clean as You Code methodology. See more details in the <a href="https://docs.sonarqube.org/latest/instance-administration/telemetry/">telemetry documentation</a>. (<a href="https://sonarsource.atlassian.net/browse/SONAR-18188">SONAR-18188</a>, <a href="https://sonarsource.atlassian.net/browse/SONAR-18219">SONAR-18219</a>).</li>\n<li>We’ve made new accessibility improvements on various pages. (<a href="https://sonarsource.atlassian.net/browse/SONAR-18131">SONAR-18131</a>, <a href="https://sonarsource.atlassian.net/browse/SONAR-17845">SONAR-17845</a>).</li>\n<li>The Docker image is now available for arm64-based Apple Silicon (M1).</li>\n</ul>\n<p>You’ll find more details in the <a href="https://docs.sonarqube.org/latest/setup-and-upgrade/release-upgrade-notes/">upgrade notes</a> and full details in the <a href="https://sonarsource.atlassian.net/issues/?jql=project%20%3D%2010139%20AND%20fixVersion%20%3D%2013931">release notes</a>.</p>\n<p>If you’re upgrading across multiple versions, you should at a minimum read the upgrade notes for the intervening versions. If you’re upgrading from the previous LTS (8.9), you’ll find a consolidated version in the <a href="https://docs.sonarqube.org/9.9/setup-and-upgrade/lts-to-lts-release-upgrade-notes/">LTS to LTS upgrade notes</a>. Also don’t forget that if you run a version older than the previous LTS (8.9), you need to upgrade to 8.9.10 first, and then to 9.9 LTS.</p>\n<p>Please open new threads for any questions you have about these or other features.</p>\n<p>As usual, <a href="https://www.sonarsource.com/products/sonarqube/downloads/">downloads are available at sonarsource.com</a>. Docker images are also available on <a href="https://hub.docker.com/_/sonarqube">Docker Hub</a>.</p>\n<p>&nbsp;<br />\nVivek &amp; Chris</p>\n            <p><small>9 posts - 5 participants</small></p>\n            <p><a href="https://community.sonarsource.com/t/sonarqube-9-9-lts-released/83246">Read full topic</a></p>', 
'summary_detail': {'type': 'text/html', 'language': None, 'base': 'https://community.sonarsource.com/c/sq/releases/24.rss', 'value': '<p>Hi all,</p>\n<p>SonarSource is thrilled to announce the release of SonarQube 9.9, the new LTS! <img alt=":tada:" height="20" src="https://europe1.discourse-cdn.com/sonarsource/uploads/sonarcommunity/original/2X/e/e69717ced28a53ad899c5024deac74a0b929ddd1.png" title=":tada:" width="20" /></p>\n<p>You’ll find a summary of all the new features added since the previous LTS in the <a href="https://www.sonarsource.com/products/sonarqube/downloads/lts/9-9-lts/">official announcement</a>. You can take a look at the highlights there, see all the great features we’ve worked on since the previous LTS including faster Pull Request analysis, securing cloud native apps, enterprise-grade features for easy operability, security and management of your instance.</p>\n<p>In addition, there are a few other items to note since the last (9.8) release:</p>\n<ul>\n<li>The SonarQube server now requires Java 17. Analysis may continue to use Java 11 if necessary. (<a href="https://sonarsource.atlassian.net/browse/SONAR-17566">SONAR-17566</a>).</li>\n<li>We’ve updated the list of supported database versions. See more details in the <a href="https://docs.sonarqube.org/latest/requirements/prerequisites-and-overview/">prerequisites documentation</a>. (<a href="https://sonarsource.atlassian.net/browse/SONAR-17712">SONAR-17712</a>, <a href="https://sonarsource.atlassian.net/browse/SONAR-17713">SONAR-17713</a>, <a href="https://sonarsource.atlassian.net/browse/SONAR-17742">SONAR-17742</a>).</li>\n<li>We’ve also updated the list of supported DevOps platform versions. See more details in the documentation, such as for example in the <a href="https://docs.sonarqube.org/latest/devops-platform-integration/github-integration/">documentation for GitHub</a>. (<a href="https://sonarsource.atlassian.net/browse/SONAR-17756">SONAR-17756</a>).</li>\n<li>We’ve improved the user experience for Quality Gates to help everyone implement the <a href="https://docs.sonarqube.org/latest/user-guide/clean-as-you-code/#quality-gate">Clean as You Code methodology</a>. SonarQube helps you identify and fix Quality Gates that are not compliant with Clean as You Code. (<a href="https://sonarsource.atlassian.net/browse/SONAR-17815">SONAR-17815</a>, <a href="https://sonarsource.atlassian.net/browse/SONAR-17816">SONAR-17816</a>, <a href="https://sonarsource.atlassian.net/browse/SONAR-17818">SONAR-17818</a>)</li>\n<li>We’ve also added information in telemetry to better understand the impact of the Clean as You Code methodology. See more details in the <a href="https://docs.sonarqube.org/latest/instance-administration/telemetry/">telemetry documentation</a>. (<a href="https://sonarsource.atlassian.net/browse/SONAR-18188">SONAR-18188</a>, <a href="https://sonarsource.atlassian.net/browse/SONAR-18219">SONAR-18219</a>).</li>\n<li>We’ve made new accessibility improvements on various pages. (<a href="https://sonarsource.atlassian.net/browse/SONAR-18131">SONAR-18131</a>, <a href="https://sonarsource.atlassian.net/browse/SONAR-17845">SONAR-17845</a>).</li>\n<li>The Docker image is now available for arm64-based Apple Silicon (M1).</li>\n</ul>\n<p>You’ll find more details in the <a href="https://docs.sonarqube.org/latest/setup-and-upgrade/release-upgrade-notes/">upgrade notes</a> and full details in the <a href="https://sonarsource.atlassian.net/issues/?jql=project%20%3D%2010139%20AND%20fixVersion%20%3D%2013931">release notes</a>.</p>\n<p>If you’re upgrading across multiple versions, you should at a minimum read the upgrade notes for the intervening versions. If you’re upgrading from the previous LTS (8.9), you’ll find a consolidated version in the <a href="https://docs.sonarqube.org/9.9/setup-and-upgrade/lts-to-lts-release-upgrade-notes/">LTS to LTS upgrade notes</a>. Also don’t forget that if you run a version older than the previous LTS (8.9), you need to upgrade to 8.9.10 first, and then to 9.9 LTS.</p>\n<p>Please open new threads for any questions you have about these or other features.</p>\n<p>As usual, <a href="https://www.sonarsource.com/products/sonarqube/downloads/">downloads are available at sonarsource.com</a>. Docker images are also available on <a href="https://hub.docker.com/_/sonarqube">Docker Hub</a>.</p>\n<p>&nbsp;<br />\nVivek &amp; Chris</p>\n            <p><small>9 posts - 5 participants</small></p>\n            <p><a href="https://community.sonarsource.com/t/sonarqube-9-9-lts-released/83246">Read full topic</a></p>'}, 
'links': [
		{'rel': 'alternate', 'type': 'text/html', 
			'href': 'https://community.sonarsource.com/t/sonarqube-9-9-lts-released/83246'}], 
'link': 'https://community.sonarsource.com/t/sonarqube-9-9-lts-released/83246', 
'published': 'Tue, 07 Feb 2023 08:28:34 +0000', 
'published_parsed': 
		time.struct_time(
				tm_year=2023, 
				tm_mon=2, 
				tm_mday=7, 
				tm_hour=8, 
				tm_min=28, 
				tm_sec=34, 
				tm_wday=1, 
				tm_yday=38, 
				tm_isdst=0), 
'discourse_topicpinned': 'No', 
'discourse_topicclosed': 'No', 
'discourse_topicarchived': 'No', 
'id': 'community.sonarsource.com-topic-83246', 
'guidislink': False, 
'source': 
			{'href': 'https://community.sonarsource.com/t/sonarqube-9-9-lts-released/83246.rss', 
				'title': 'SonarQube 9.9 LTS released'}
}
```

## Dependency Check Feed

URL

```bash
https://github.com/jeremylong/DependencyCheck/releases.atom
```

Key components

```bash
'title': 'Version 8.1.0', 
'updated': '2023-02-13T11:34:53Z', 
'summary': '<h3>Added</h3>\n<ul>\n<li><code>Pipefile.lock</code> files are now supported (<a href="https://github.com/jeremylong/DependencyCheck/pull/5404">#5404</a>).</li>\n<li>Python projects with only a <code>pyproject.toml</code> but no lock file or requirements will report an error as ODC is unable to analyze the project (<a href="https://github.com/jeremylong/DependencyCheck/pull/5409">#5409</a>).</li>\n</ul>\n<h3>Fixed</h3>\n<ul>\n<li>Some maven projects caused false positives due to bad string interpolation (<a href="https://github.com/jeremylong/DependencyCheck/pull/5421">#5421</a>).</li>\n<li>Error message from Assembly Analyzer has been updated to emphasize dotnet 6 is required for analysis (<a href="https://github.com/jeremylong/DependencyCheck/pull/5408">#5408</a>).</li>\n<li>Correct issue where database defrag occurs even when no updates were performed (<a href="https://github.com/jeremylong/DependencyCheck/pull/5441">#5441</a>).</li>\n<li>Fixed several False Positives and one False Negative.</li>\n<li>Fixed the <code>format</code> configuration more flexible in the gradle plugin (<a href="https://github.com/dependency-check/dependency-check-gradle/pull/324">dependency-check-gradle/#324</a>).</li>\n</ul>\n<p>See the full listing of <a href="https://github.com/jeremylong/DependencyCheck/milestone/60?closed=1">changes</a>.</p>', 
'link': 'https://github.com/jeremylong/DependencyCheck/releases/tag/v8.1.0'
```

Constraint

- Cannot filter pre-releases as there is no identifier within entry to distinguish release types
    - Requires Gitlab API

raw sample rss entry

```bash
{
'id': 'tag:github.com,2008:Repository/5663857/v8.1.0', 
'guidislink': True, 
'link': 'https://github.com/jeremylong/DependencyCheck/releases/tag/v8.1.0', 
'updated': '2023-02-13T11:34:53Z', 
'updated_parsed': 
		time.struct_time(
				tm_year=2023, 
				tm_mon=2,
				tm_mday=13, 
				tm_hour=11, 
				tm_min=34, 
				tm_sec=53, 
				tm_wday=0, 
				tm_yday=44, 
				tm_isdst=0), 
'links': [
		{'rel': 'alternate', 'type': 'text/html', 
			'href': 'https://github.com/jeremylong/DependencyCheck/releases/tag/v8.1.0'}
], 
'title': ```bash
{
'id': 'tag:github.com,2008:Repository/5663857/v8.1.0', 
'guidislink': True, 
'link': 'https://github.com/jeremylong/DependencyCheck/releases/tag/v8.1.0', 
'updated': '2023-02-13T11:34:53Z', 
'updated_parsed': 
		time.struct_time(
				tm_year=2023, 
				tm_mon=2,
				tm_mday=13, 
				tm_hour=11, 
				tm_min=34, 
				tm_sec=53, 
				tm_wday=0, 
				tm_yday=44, 
				tm_isdst=0), 
'links': [
		{'rel': 'alternate', 'type': 'text/html', 
			'href': 'https://github.com/jeremylong/DependencyCheck/releases/tag/v8.1.0'}
], 
'title': 'Version 8.1.0', 
'title_detail': 
		{'type': 'text/plain', 
			'language': 'en-US', 
			'base': 'https://github.com/jeremylong/DependencyCheck/releases.atom', 
			'value': 'Version 8.1.0'}, 
'content': [
		{'type': 'text/html', 'language': 'en-US', 
			'base': 'https://github.com/jeremylong/DependencyCheck/releases.atom', 
			'value': '<h3>Added</h3>\n<ul>\n<li><code>Pipefile.lock</code> files are now supported (<a href="https://github.com/jeremylong/DependencyCheck/pull/5404">#5404</a>).</li>\n<li>Python projects with only a <code>pyproject.toml</code> but no lock file or requirements will report an error as ODC is unable to analyze the project (<a href="https://github.com/jeremylong/DependencyCheck/pull/5409">#5409</a>).</li>\n</ul>\n<h3>Fixed</h3>\n<ul>\n<li>Some maven projects caused false positives due to bad string interpolation (<a href="https://github.com/jeremylong/DependencyCheck/pull/5421">#5421</a>).</li>\n<li>Error message from Assembly Analyzer has been updated to emphasize dotnet 6 is required for analysis (<a href="https://github.com/jeremylong/DependencyCheck/pull/5408">#5408</a>).</li>\n<li>Correct issue where database defrag occurs even when no updates were performed (<a href="https://github.com/jeremylong/DependencyCheck/pull/5441">#5441</a>).</li>\n<li>Fixed several False Positives and one False Negative.</li>\n<li>Fixed the <code>format</code> configuration more flexible in the gradle plugin (<a href="https://github.com/dependency-check/dependency-check-gradle/pull/324">dependency-check-gradle/#324</a>).</li>\n</ul>\n<p>See the full listing of <a href="https://github.com/jeremylong/DependencyCheck/milestone/60?closed=1">changes</a>.</p>'}
], 
'summary': '<h3>Added</h3>\n<ul>\n<li><code>Pipefile.lock</code> files are now supported (<a href="https://github.com/jeremylong/DependencyCheck/pull/5404">#5404</a>).</li>\n<li>Python projects with only a <code>pyproject.toml</code> but no lock file or requirements will report an error as ODC is unable to analyze the project (<a href="https://github.com/jeremylong/DependencyCheck/pull/5409">#5409</a>).</li>\n</ul>\n<h3>Fixed</h3>\n<ul>\n<li>Some maven projects caused false positives due to bad string interpolation (<a href="https://github.com/jeremylong/DependencyCheck/pull/5421">#5421</a>).</li>\n<li>Error message from Assembly Analyzer has been updated to emphasize dotnet 6 is required for analysis (<a href="https://github.com/jeremylong/DependencyCheck/pull/5408">#5408</a>).</li>\n<li>Correct issue where database defrag occurs even when no updates were performed (<a href="https://github.com/jeremylong/DependencyCheck/pull/5441">#5441</a>).</li>\n<li>Fixed several False Positives and one False Negative.</li>\n<li>Fixed the <code>format</code> configuration more flexible in the gradle plugin (<a href="https://github.com/dependency-check/dependency-check-gradle/pull/324">dependency-check-gradle/#324</a>).</li>\n</ul>\n<p>See the full listing of <a href="https://github.com/jeremylong/DependencyCheck/milestone/60?closed=1">changes</a>.</p>', 
'authors': [{'name': 'github-actions[bot]'}], 
'author_detail': {'name': 'github-actions[bot]'}, 
'author': 'github-actions[bot]', 
'media_thumbnail': [
		{'height': '30', 'width': '30', 'url': 'https://avatars.githubusercontent.com/in/15368?s=60&v=4'}
], 
'href': ''
}
```
'title_detail': 
		{'type': 'text/plain', 
			'language': 'en-US', 
			'base': 'https://github.com/jeremylong/DependencyCheck/releases.atom', 
			'value': 'Version 8.1.0'}, 
'content': [
		{'type': 'text/html', 'language': 'en-US', 
			'base': 'https://github.com/jeremylong/DependencyCheck/releases.atom', 
			'value': '<h3>Added</h3>\n<ul>\n<li><code>Pipefile.lock</code> files are now supported (<a href="https://github.com/jeremylong/DependencyCheck/pull/5404">#5404</a>).</li>\n<li>Python projects with only a <code>pyproject.toml</code> but no lock file or requirements will report an error as ODC is unable to analyze the project (<a href="https://github.com/jeremylong/DependencyCheck/pull/5409">#5409</a>).</li>\n</ul>\n<h3>Fixed</h3>\n<ul>\n<li>Some maven projects caused false positives due to bad string interpolation (<a href="https://github.com/jeremylong/DependencyCheck/pull/5421">#5421</a>).</li>\n<li>Error message from Assembly Analyzer has been updated to emphasize dotnet 6 is required for analysis (<a href="https://github.com/jeremylong/DependencyCheck/pull/5408">#5408</a>).</li>\n<li>Correct issue where database defrag occurs even when no updates were performed (<a href="https://github.com/jeremylong/DependencyCheck/pull/5441">#5441</a>).</li>\n<li>Fixed several False Positives and one False Negative.</li>\n<li>Fixed the <code>format</code> configuration more flexible in the gradle plugin (<a href="https://github.com/dependency-check/dependency-check-gradle/pull/324">dependency-check-gradle/#324</a>).</li>\n</ul>\n<p>See the full listing of <a href="https://github.com/jeremylong/DependencyCheck/milestone/60?closed=1">changes</a>.</p>'}
], 
'summary': '<h3>Added</h3>\n<ul>\n<li><code>Pipefile.lock</code> files are now supported (<a href="https://github.com/jeremylong/DependencyCheck/pull/5404">#5404</a>).</li>\n<li>Python projects with only a <code>pyproject.toml</code> but no lock file or requirements will report an error as ODC is unable to analyze the project (<a href="https://github.com/jeremylong/DependencyCheck/pull/5409">#5409</a>).</li>\n</ul>\n<h3>Fixed</h3>\n<ul>\n<li>Some maven projects caused false positives due to bad string interpolation (<a href="https://github.com/jeremylong/DependencyCheck/pull/5421">#5421</a>).</li>\n<li>Error message from Assembly Analyzer has been updated to emphasize dotnet 6 is required for analysis (<a href="https://github.com/jeremylong/DependencyCheck/pull/5408">#5408</a>).</li>\n<li>Correct issue where database defrag occurs even when no updates were performed (<a href="https://github.com/jeremylong/DependencyCheck/pull/5441">#5441</a>).</li>\n<li>Fixed several False Positives and one False Negative.</li>\n<li>Fixed the <code>format</code> configuration more flexible in the gradle plugin (<a href="https://github.com/dependency-check/dependency-check-gradle/pull/324">dependency-check-gradle/#324</a>).</li>\n</ul>\n<p>See the full listing of <a href="https://github.com/jeremylong/DependencyCheck/milestone/60?closed=1">changes</a>.</p>', 
'authors': [{'name': 'github-actions[bot]'}], 
'author_detail': {'name': 'github-actions[bot]'}, 
'author': 'github-actions[bot]', 
'media_thumbnail': [
		{'height': '30', 'width': '30', 'url': 'https://avatars.githubusercontent.com/in/15368?s=60&v=4'}
], 
'href': ''
}
```
