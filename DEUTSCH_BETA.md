# Private Deutsch Beta B001

This branch builds Installer 1.3.0 Private Beta B001, not a published release.
The released English 1.2.1 executable and KKS 1.1.0 package are unchanged.

The fixed German catalog replaces `fonts_en.swf`, `fontconfig_de.txt` and
`translate_de.txt` in their existing archives and installs the three German
string tables. It requires the original verified Steam build and a signed
German package. English archive members and loose string tables are preserved.
Package manifests cannot select arbitrary languages, members or paths.

English/Deutsch in the interface changes the installer language only. The ZIP
selects the content language; Steam selects the game's language. Common screens
and operational messages are localized. Uncatalogued technical diagnostics may
still appear in English during this private beta.

Restore vanilla before switching content languages. German and English package
sequences and release identities are independent. The first successful German
installation upgrades local history to schema 3; subsequent English installations
preserve it. Use this 1.3.0 installer for repair, restore and return to English
after testing Deutsch. The older 1.2.1 installer cannot read schema 3.
Existing English-only histories remain schema 2 until German is installed.

Author a German package with `build_content.py build --language de
--translation-localization` and the usual explicit signing and baseline inputs.
Beta status is also recorded in the signed QA metadata and build label. The
manifest retains the existing release envelope; no public release is implied.

Run the complete locked-toolchain build, including the tests, before handing off
an executable. Additional tests cover German install/repair/restore, preserving
English resources, interruption recovery, independent sequence histories, strict
profile validation, interface switching and the smallest supported window.

Content authoring, exact baseline evidence and private tester artifacts live in
`KKS_Master/Features/Localization/Deutsch_B001`. Native-language in-game review
remains the acceptance gate. Do not publish this branch or its artifacts yet.
