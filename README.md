# tap-bing-ads

## Metadata Reference

tap-bing-ads uses some custom metadata keys:

* `fieldExclusions` - Indicates which other fields may not be selected when this field is selected. If you invoke the tap with selections that violate fieldExclusion rules, it is likely that the tap will fail.

## Listing Accessible Accounts

Some Microsoft Ads users authenticate via delegated access and may not own the
underlying accounts. The tap now uses the `SearchAccounts` API to enumerate all
accounts that the OAuth token can access. During discovery the first account id
provided in the configuration must be present in this list otherwise an error is
raised. This mirrors how tools such as Fivetran handle delegated account access.

---

Copyright &copy; 2017 Stitch
