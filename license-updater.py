#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Koordinates simple license updater utility.

This tool takes an input file of layer IDs for a Koordinates
site and updates the relevant layers with a different license.

Examaple usage:

    python license-updater.py --host [site] --t [key] --license 171 --reference "Licence updated to CCBY 4.0"

"""
import csv
import sys
import time
import logging
import argparse
import koordinates


logging.basicConfig(level=logging.ERROR)


def run():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-d', '--host', dest='host', help='Site domain/host', required=True)
    parser.add_argument('-t', '--token', dest='token', help='Site API Key', required=True)
    parser.add_argument('-l', '--license', dest='license', help='Licence ID to update layers to', required=True)
    parser.add_argument('-r', '--reference', dest='reference', help='Version reference', default='')
    parser.add_argument('-n', '--dry-run', dest='dry_run', action='store_true', help='Check versions without making changes', default=False)
    parser.add_argument('fin', help='Input CSV contained layer "ID" column', type=argparse.FileType('r'))
    options = vars(parser.parse_args())

    # Create our client
    client = koordinates.Client(options['host'], token=options['token'])

    # Read, clean and validate input IDs:
    csv_reader = csv.DictReader(options['fin'])
    if 'ID' not in csv_reader.fieldnames:
        sys.stderr.write("Could not find column 'ID' in supplied CSV, aborting.\n")
        sys.exit(1)

    try:
        layer_ids = [int(row['ID'].strip()) for row in csv_reader]
        layer_count = len(layer_ids)
    except ValueError:
        sys.stderr.write("Could not parse layer ID list from input file, aborting.\n")
        sys.exit(1)

    if not layer_ids:
        sys.stderr.write("No valid layer IDs supplied, aborting.\n")
        sys.exit(1)


    # Fetch and validate the new license:
    new_license = client.licenses.get(options['license'])
    ret = raw_input("Update {} layers with licence '{}'? [y/N] ".format(layer_count, new_license.title))
    if ret not in ['y', 'Y']:
        sys.exit()


    # Initialize a publishing object:
    publish = koordinates.publishing.Publish(reference='license-update')
    layer_ids_updated = []

    sys.stdout.write("Updating licenses for {} layer drafts:\n".format(layer_count))

    for idx, layer_id in enumerate(layer_ids):

        sys.stdout.write(" • {}/{} Processing layer ID: {}\n".format(idx+1, layer_count, layer_id))

        # Get the layer
        try:
            layer = client.layers.get(layer_id)
            sys.stdout.write("    Found layer: {}\n".format(layer.title.encode('utf8')))
        except koordinates.exceptions.NotFound:
            sys.stderr.write("    No layer found, skipping.\n")
            continue

        # Check current license. Skip this layer if it's already correct:
        sys.stdout.write("       Current license: {}\n".format(layer.license.title.encode('utf8') if layer.license else "not set"))
        if layer.license and layer.license.id == new_license.id:
            sys.stdout.write("          License is already correct, skipping!\n")
            continue

        # No-op if a dry-run:
        if options['dry_run']:
            try:
                layer_draft = layer.get_draft_version()
                sys.stdout.write("       Draft version found (will be deleted). \n")
            except koordinates.exceptions.NotFound:
                pass
            continue

        # Create a fresh draft, deleting old ones if they already exist:
        layer_draft = None
        try:
            layer_draft = layer.get_draft_version()
            sys.stdout.write("       Draft version found. Removing existing draft... ")
        except koordinates.exceptions.NotFound:
            pass
        if layer_draft:
            layer_draft.delete_version()
            sys.stdout.write("✔︎\n")
        sys.stdout.write("       Creating new draft version... ")
        layer_draft = layer.create_draft_version()
        sys.stdout.write("✔︎\n")

        # Set draft version license
        sys.stdout.write("       Setting draft reference & license... ")
        layer_draft.license = new_license
        layer_draft.reference = options['reference']
        layer_draft.save()
        sys.stdout.write("✔︎\n")

        # Add to pending publish list:
        layer_ids_updated.append(layer_id)
        publish.add_layer_item(layer_draft)

    if options['dry_run']:
        sys.stdout.write(" • Ending dry run.\n")
        sys.exit(0)

    # Check we've got drafts to publish:
    if not publish.items:
        sys.stdout.write(" • Nothing to publish!\n")
        sys.exit(0)

    # Submit for publishing:
    sys.stdout.write("\n")
    sys.stdout.write("Publish: Submitting drafts for publishing... ")
    publish = client.publishing.create(publish)
    sys.stdout.write("✔︎\n")

    sys.stdout.write(" • Waiting for completion")

    while publish.state != 'completed':
        sys.stdout.write(".")
        sys.stdout.flush()
        time.sleep(2)
        publish.refresh()

        # we have not imported any new data and we're publishing immediately, so these
        # are the only two states we expect to see:
        if publish.state not in ['publishing', 'completed']:
            sys.stderr.write("unexpected publishing state for publish id: {} (state:{}), aborting.".format(publish.id, publish.state))
            sys.exit(1)

    sys.stdout.write(" ✔︎\n\n")

    # Verify changes
    layer_ids_updated_count = len(layer_ids_updated)
    sys.stdout.write("Verifying updates to {} layers:\n".format(layer_ids_updated_count))
    for idx, layer_id in enumerate(layer_ids_updated):
        layer = client.layers.get(layer_id)
        sys.stdout.write(" • {}/{} {} {}\n".format(
            idx+1,
            layer_ids_updated_count,
            layer.title.encode('utf8'),
            "✔︎" if (layer.license.encode('utf8') and layer.license.id == new_license.id) else "⨯"
        ))
    sys.exit(0)


if __name__ == "__main__":
    # entry point
    run()
