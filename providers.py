# coding=utf-8
"""
Various provider-related configurations
"""
from collections import namedtuple

DnsProvider = namedtuple("DnsProvider",
                         "name_option "
                         "secret_path_option "
                         "propagation_time_option")

providers = {
    "cloudflare": DnsProvider(
        "--dns-cloudflare",
        "--dns-cloudflare-credentials",
        "--dns-cloudflare-propagation-seconds"),
    "cloudxns": DnsProvider(
        "--dns-cloudxns",
        "--dns-cloudxns-credentials",
        "--dns-cloudxns-propagation-seconds"),
    "digitalocean": DnsProvider(
        "--dns-digitalocean",
        "--dns-digitalocean-credentials",
        "--dns-digitalocean-propagation-seconds"),
    "dnsimple": DnsProvider(
        "--dns-dnsimple",
        "--dns-dnsimple-credentials",
        "--dns-dnsimple-propagation-seconds",
    ),
    "dnsmadeeasy": DnsProvider(
        "--dns-dnsmadeeasy",
        "--dns-dnsmadeeasy-credentials",
        "--dns-dnsmadeeasy-propagation-seconds",
    ),
    "gehirn": DnsProvider(
        "--dns-gehirn",
        "--dns-gehirn-credentials",
        "--dns-gehirn-propagation-seconds",
    ),
    "google": DnsProvider(
        "--dns-google",
        "--dns-google-credentials",
        "--dns-google-propagation-seconds",
    ),
    "linode": DnsProvider(
        "--dns-linode",
        "--dns-linode-credentials",
        "--dns-linode-propagation-seconds",
    ),
    "luadns": DnsProvider(
        "--dns-luadns",
        "--dns-luadns-credentials",
        "--dns-luadns-propagation-seconds",
    ),
    "nsone": DnsProvider(
        "--dns-nsone",
        "--dns-nsone-credentials",
        "--dns-nsone-propagation-seconds",
    ),
    "ovh": DnsProvider(
        "--dns-ovh",
        "--dns-ovh-credentials",
        "--dns-ovh-propagation-seconds",
    ),
    "rfc2136": DnsProvider(
        "--dns-rfc2136",
        "--dns-rfc2136-credentials",
        "--dns-rfc2136-propagation-seconds",
    ),
    "route53": DnsProvider(
        "--dns-route53",
        "--dns-route53-credentials",  # not used actually
        "--dns-route53-propagation-seconds",
    ),
    "godaddy": DnsProvider(
        "--authenticator dns-godaddy",  # not a typo, split is applied
        "--dns-godaddy-credentials",
        "--dns-godaddy-propagation-seconds"
    ),
    "sakuracloud": DnsProvider(
        "--dns-sakuracloud",
        "--dns-sakuracloud-credentials",
        "--dns-sakuracloud-propagation-seconds",
    ),
}
