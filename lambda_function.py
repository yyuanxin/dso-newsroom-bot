import classes as rss

burp = rss.BurpsuiteRSS("Burpsuite", "https://portswigger.net/burp/releases/rss")
gitlab = rss.GitlabRSS("Gitlab", "https://about.gitlab.com/all-releases.xml")
# gitlab_breaking_changes = rss.CommonRSS("Gitlab Breaking Changes", "https://about.gitlab.com/breaking-changes.xml")
# openssl = rss.OpensslRSS("OpenSSL", "https://github.com/openssl/openssl/releases.atom")
# iam_authenticator = rss.GithubRSS("AWS IAM Authenticator", "https://github.com/kubernetes-sigs/aws-iam-authenticator/releases.atom")
# helm = rss.GithubRSS("Helm", "https://github.com/helm/helm/releases.atom")
aws_cli = rss.AwsCliRSS("AWS CLI", "https://github.com/aws/aws-cli/tags.atom")
correto_11 = rss.GithubRSS("Correto 11", "https://github.com/corretto/corretto-11/releases.atom")
correto_17 = rss.GithubRSS("Correto 17", "https://github.com/corretto/corretto-17/releases.atom")
maven = rss.GithubRSS("Maven", "https://github.com/apache/maven/releases.atom")
nodejs = rss.NodejsRSS("Nodejs", "https://github.com/nodejs/node/releases.atom")
sonar_scanner = rss.GithubRSS("Sonar Scanner CLI", "https://github.com/SonarSource/sonar-scanner-cli/releases.atom")
sonarqube = rss.SonarqubeRSS("Sonarqube", "https://community.sonarsource.com/c/sq/releases/24.rss")
dependency_check = rss.GithubRSS("Dependency Check", "https://github.com/jeremylong/DependencyCheck/releases.atom")

lst = [
    burp,
    gitlab,
    # gitlab_breaking_changes,
    # openssl,
    # iam_authenticator,
    # helm,
    aws_cli,
    correto_11,
    correto_17,
    maven,
    nodejs,
    sonar_scanner,
    sonarqube,
    dependency_check
]

def lambda_handler(event, context):

    rss.loadCached()
    for i in lst:
        print(i.name)
        if isinstance(i, rss.RSS):
            i.checkRSS()
    rss.uploadCached()

    # TODO implement
    return {
        'statusCode': 200,
        'body': "Hello from Lambda!"
    }