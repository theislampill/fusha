#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Self-test for public Qamus hover-detail extraction."""
import crawl_qamus_public_entries as C


def main():
    html = (
        '<span class="qword" data-tr="from" data-loc="9:69:2" data-conf="low">مِن</span>'
        '<span class="qword qw-pending" data-loc="9:69:3">قَبْلِكُمْ</span>'
    )
    rows = C.extract_hover_details(html)
    assert rows == [
        {"loc": "9:69:2", "gloss": "from", "pending": False},
        {"loc": "9:69:3", "gloss": "", "pending": True},
    ]
    print("public hover-detail extraction self-test OK")


if __name__ == "__main__":
    main()
