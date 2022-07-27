from __future__ import absolute_import

from . import box


class AdobeFragmentRandomAccess(box.FullBox):

    def parse(self, buf):
        super(AdobeFragmentRandomAccess, self).parse(buf)
        self.long_ids = buf.readbits(1)
        self.long_offsets = buf.readbits(1)
        self.global_entries_present = buf.readbits(1)
        buf.readbits(5)
        self.timescale = buf.readint32()
        self.entry_count = buf.readint32()
        self.entries = []
        for _ in range(self.entry_count):
            time = buf.readint64()
            if self.long_offsets:
                offset = buf.readint64()
            else:
                offset = buf.readint32()
            self.entries.append((time, offset))
        self.global_entry_count = 0
        self.global_entries = []
        if self.global_entries_present:
            self.global_entry_count = buf.readint32()
        for _ in range(self.global_entry_count):
            time = buf.readint64()
            if self.long_ids:
                eid = buf.readint32()
            else:
                eid = buf.readint16()
            self.entries.append((time, eid))

    def generate_fields(self):
        for x in super(AdobeFragmentRandomAccess, self).generate_fields():
            yield x
        yield box.Field("Long IDs", self.long_ids)
        yield box.Field("Long offsets", self.long_offsets)
        yield box.Field("Global entries present", self.global_entries_present)
        yield box.Field("Timescale", self.timescale)
        yield box.Field("Entry count", self.entry_count)
        i = 0
        for e in self.entries:
            i += 1
            yield box.Field("  Entry %d" % (i), e, "time=%d, offset=%d" % e)
        if self.global_entries_present:
            yield box.Field("Global entry count", self.global_entry_count)
            i = 0
            for e in self.global_entries:
                i += 1
                yield box.Field("  Global entry %d" % (i), e, "time=%d, id=%d" % e)


class AdobeBootstrap(box.FullBox):

    def parse(self, buf):
        super(AdobeBootstrap, self).parse(buf)
        self.bootstrap_info_version = buf.readint32()
        self.profile = buf.readbits(2)
        self.live = buf.readbits(1)
        self.update = buf.readbits(1)
        buf.readbits(4)
        self.timescale = buf.readint32()
        self.current_media_time = buf.readint64()
        self.smpte_time_code_offset = buf.readint64()
        self.movie_id = buf.read_cstring()
        self.server_entry_count = buf.readbyte()
        self.server_entries = []
        for _ in range(self.server_entry_count):
            self.server_entries.append(buf.read_cstring())
        self.quality_entry_count = buf.readbyte()
        self.quality_entries = []
        for _ in range(self.quality_entry_count):
            self.quality_entries.append(buf.read_cstring())
        self.drmdata = buf.read_cstring()
        self.metadata = buf.read_cstring()
        self.segment_run_table_entry_count = buf.readbyte()
        self.segment_run_table_entries = []
        for _ in range(self.segment_run_table_entry_count):
            self.segment_run_table_entries.append(AdobeSegmentRunTable(buf))
        self.fragment_run_table_entry_count = buf.readbyte()
        self.fragment_run_table_entries = []
        for _ in range(self.fragment_run_table_entry_count):
            self.fragment_run_table_entries.append(AdobeFragmentRunTable(buf))

    def generate_fields(self):
        for x in super(AdobeBootstrap, self).generate_fields():
            yield x
        yield box.Field("Profile", self.profile)
        yield box.Field("Live", self.live)
        yield box.Field("Update", self.update)
        yield box.Field("Timescale", self.timescale)
        yield box.Field("Current media time", self.current_media_time)
        yield box.Field("SMPTE time code", self.smpte_time_code_offset)
        yield box.Field("Movie ID", self.movie_id, self.movie_id if len(self.movie_id) else '<empty>')
        yield box.Field("Server entry count", self.server_entry_count)
        for s in self.server_entries:
            yield box.Field("Server", s, s if len(s) else '<empty>')
        yield box.Field("Quality entry count", self.quality_entry_count)
        for q in self.quality_entries:
            yield box.Field("Quality", q, q if len(q) else '<empty>')
        yield box.Field("DRM data", self.drmdata, self.drmdata if len(self.drmdata) else '<empty>')
        yield box.Field("Metadata", self.metadata, self.metadata if len(self.metadata) else '<empty>')
        yield box.Field("Segment run table entry count", self.segment_run_table_entry_count)
        for t in self.segment_run_table_entries:
            yield t
        yield box.Field("Fragment run table entry count", self.fragment_run_table_entry_count)
        for t in self.fragment_run_table_entries:
            yield t


class AdobeSegmentRunTable(box.FullBox):

    def parse(self, buf):
        super(AdobeSegmentRunTable, self).parse(buf)
        self.quality_entry_count = buf.readbyte()
        self.quality_url_modifiers = []
        for _ in range(self.quality_entry_count):
            self.quality_url_modifiers.append(buf.read_cstring())
        self.segment_entry_count = buf.readint32()
        self.segment_entries = []
        for _ in range(self.segment_entry_count):
            first_segment = buf.readint32()
            fragments_per_segment = buf.readint32()
            self.segment_entries.append((first_segment, fragments_per_segment))

    def generate_fields(self):
        for x in super(AdobeSegmentRunTable, self).generate_fields():
            yield x
        yield box.Field("Quality entry count", self.quality_entry_count)
        for q in self.quality_url_modifiers:
            yield box.Field("Quality url modifier", q, q if len(q) else '<empty>')
        yield box.Field("Segment entry count", self.segment_entry_count)
        i = 0
        for e in self.segment_entries:
            i += 1
            yield box.Field("Entry %d" % (i), e, "First segment=%d, Fragments per segment=%d" % e)


class AdobeFragmentRunTable(box.FullBox):

    def parse(self, buf):
        super(AdobeFragmentRunTable, self).parse(buf)
        self.timescale = buf.readint32()
        self.quality_entry_count = buf.readbyte()
        self.quality_url_modifiers = []
        for _ in range(self.quality_entry_count):
            self.quality_url_modifiers.append(buf.read_cstring())
        self.fragment_entry_count = buf.readint32()
        self.fragment_entries = []
        for _ in range(self.fragment_entry_count):
            first_fragment = buf.readint32()
            first_fragment_timestamp = buf.readint64()
            fragment_duration = buf.readint32()
            discontinuity_idicator = 0
            if fragment_duration == 0:
                discontinuity_idicator = buf.readbyte()
            self.fragment_entries.append(
                (first_fragment, first_fragment_timestamp, fragment_duration, discontinuity_idicator))

    def generate_fields(self):
        for x in super(AdobeFragmentRunTable, self).generate_fields():
            yield x
        yield box.Field("Timescale", self.timescale)
        yield box.Field("Quality entry count", self.quality_entry_count)
        for q in self.quality_url_modifiers:
            yield box.Field("Quality url modifier", q, q if len(q) else '<empty>')
        yield box.Field("Fragment entry count", self.fragment_entry_count)
        i = 0
        for e in self.fragment_entries:
            i += 1
            yield box.Field("Entry %d" % (i), e,
                        "first fragment=%d, first fragment timestamp=%d, fragment duration=%d, discontinuity=%d" % e)


boxmap = {
    'afra': AdobeFragmentRandomAccess,
    'abst': AdobeBootstrap,
    'asrt': AdobeSegmentRunTable,
    'afrt': AdobeFragmentRunTable,
}
