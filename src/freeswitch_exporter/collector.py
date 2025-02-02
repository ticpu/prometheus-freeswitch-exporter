"""
Prometheus collectors for FreeSWITCH.
"""
# pylint: disable=too-few-public-methods

# commands in use by this collector
#
# api json {"command": "status", "data": ""}
# api json {"command": "show calls", "data": ""}
# api json {"command": "sofia", "data": ""}
#
# api sofia status
# api sofia status profile internal


import asyncio
import itertools
import json
import logging

from prometheus_client import CollectorRegistry, generate_latest
from prometheus_client.core import GaugeMetricFamily

from freeswitch_exporter.esl import ESL
from freeswitch_exporter.sofia_status import SofiaProfile, SofiaProfileStatus


class ESLProcessInfo:
    """
    Process info async collector
    """

    def __init__(self, esl: ESL):
        self._esl = esl

    async def collect(self):
        """
        Collects FreeSWITCH process info metrics.
        """

        (_, result) = await self._esl.send(
            'api json {"command" : "status", "data" : ""}')
        response = json.loads(result).get('response', {})

        process_info_metric = GaugeMetricFamily(
            'freeswitch_info',
            'FreeSWITCH info',
            labels=['version'])
        if 'version' in response:
            process_info_metric.add_metric([response['version']], 1)

        process_status_metric = GaugeMetricFamily(
            'freeswitch_up',
            'FreeSWITCH ready status',
        )
        if 'systemStatus' in response:
            status = int(response['systemStatus'] == 'ready')
            process_status_metric.add_metric([], status)

        process_memory_metric = GaugeMetricFamily(
            'freeswitch_stack_bytes',
            'FreeSWITCH stack size',
        )
        if 'stackSizeKB' in response:
            memory = response['stackSizeKB'].get('current', 0)
            process_memory_metric.add_metric([], memory * 1024)

        process_session_metrics = []
        if 'sessions' in response:
            for metric in ['total', 'active', 'limit']:
                process_session_metric = GaugeMetricFamily(
                    'freeswitch_session_%s' % (metric,),
                    'FreeSWITCH %s number of sessions' % (metric,),
                )

                value = response['sessions'].get('count', {}).get(metric, 0)
                process_session_metric.add_metric([], value)

                process_session_metrics.append(process_session_metric)

        return itertools.chain([
            process_info_metric,
            process_status_metric,
            process_memory_metric
        ], process_session_metrics)


class ESLChannelInfo:
    """
    Channel info async collector
    """

    def __init__(self, esl: ESL):
        self._esl = esl
        self._log = logging.getLogger(__name__)

    async def collect(self):
        """
        Collects channel metrics.
        """

        channel_metrics = {
            'variable_rtp_audio_in_raw_bytes': GaugeMetricFamily(
                'rtp_audio_in_raw_bytes_total',
                'Total number of bytes received via this channel.',
                labels=['id']),
            'variable_rtp_audio_out_raw_bytes': GaugeMetricFamily(
                'rtp_audio_out_raw_bytes_total',
                'Total number of bytes sent via this channel.',
                labels=['id']),
            'variable_rtp_audio_in_media_bytes': GaugeMetricFamily(
                'rtp_audio_in_media_bytes_total',
                'Total number of media bytes received via this channel.',
                labels=['id']),
            'variable_rtp_audio_out_media_bytes': GaugeMetricFamily(
                'rtp_audio_out_media_bytes_total',
                'Total number of media bytes sent via this channel.',
                labels=['id']),
            'variable_rtp_audio_in_packet_count': GaugeMetricFamily(
                'rtp_audio_in_packets_total',
                'Total number of packets received via this channel.',
                labels=['id']),
            'variable_rtp_audio_out_packet_count': GaugeMetricFamily(
                'rtp_audio_out_packets_total',
                'Total number of packets sent via this channel.',
                labels=['id']),
            'variable_rtp_audio_in_media_packet_count': GaugeMetricFamily(
                'rtp_audio_in_media_packets_total',
                'Total number of media packets received via this channel.',
                labels=['id']),
            'variable_rtp_audio_out_media_packet_count': GaugeMetricFamily(
                'rtp_audio_out_media_packets_total',
                'Total number of media packets sent via this channel.',
                labels=['id']),
            'variable_rtp_audio_in_skip_packet_count': GaugeMetricFamily(
                'rtp_audio_in_skip_packets_total',
                'Total number of inbound packets discarded by this channel.',
                labels=['id']),
            'variable_rtp_audio_out_skip_packet_count': GaugeMetricFamily(
                'rtp_audio_out_skip_packets_total',
                'Total number of outbound packets discarded by this channel.',
                labels=['id']),
            'variable_rtp_audio_in_jitter_packet_count': GaugeMetricFamily(
                'rtp_audio_in_jitter_packets_total',
                'Total number of ? packets in this channel.',
                labels=['id']),
            'variable_rtp_audio_in_dtmf_packet_count': GaugeMetricFamily(
                'rtp_audio_in_dtmf_packets_total',
                'Total number of ? packets in this channel.',
                labels=['id']),
            'variable_rtp_audio_out_dtmf_packet_count': GaugeMetricFamily(
                'rtp_audio_out_dtmf_packets_total',
                'Total number of ? packets in this channel.',
                labels=['id']),
            'variable_rtp_audio_in_cng_packet_count': GaugeMetricFamily(
                'rtp_audio_in_cng_packets_total',
                'Total number of ? packets in this channel.',
                labels=['id']),
            'variable_rtp_audio_out_cng_packet_count': GaugeMetricFamily(
                'rtp_audio_out_cng_packets_total',
                'Total number of ? packets in this channel.',
                labels=['id']),
            'variable_rtp_audio_in_flush_packet_count': GaugeMetricFamily(
                'rtp_audio_in_flush_packets_total',
                'Total number of ? packets in this channel.',
                labels=['id']),
            'variable_rtp_audio_in_largest_jb_size': GaugeMetricFamily(
                'rtp_audio_in_jitter_buffer_bytes_max',
                'Largest jitterbuffer size in this channel.',
                labels=['id']),
            'variable_rtp_audio_in_jitter_min_variance': GaugeMetricFamily(
                'rtp_audio_in_jitter_seconds_min',
                'Minimal jitter in seconds.',
                labels=['id']),
            'variable_rtp_audio_in_jitter_max_variance': GaugeMetricFamily(
                'rtp_audio_in_jitter_seconds_max',
                'Maximum jitter in seconds.',
                labels=['id']),
            'variable_rtp_audio_in_jitter_loss_rate': GaugeMetricFamily(
                'rtp_audio_in_jitter_loss_rate',
                'Ratio of lost packets due to inbound jitter.',
                labels=['id']),
            'variable_rtp_audio_in_jitter_burst_rate': GaugeMetricFamily(
                'rtp_audio_in_jitter_burst_rate',
                'Ratio of packet bursts due to inbound jitter.',
                labels=['id']),
            'variable_rtp_audio_in_mean_interval': GaugeMetricFamily(
                'rtp_audio_in_mean_interval_seconds',
                'Mean interval in seconds of inbound packets',
                labels=['id']),
            'variable_rtp_audio_in_flaw_total': GaugeMetricFamily(
                'rtp_audio_in_flaw_total',
                'Total number of flaws detected in the channel',
                labels=['id']),
            'variable_rtp_audio_in_quality_percentage': GaugeMetricFamily(
                'rtp_audio_in_quality_percent',
                'Audio quality in percent',
                labels=['id']),
            'variable_rtp_audio_in_mos': GaugeMetricFamily(
                'rtp_audio_in_quality_mos',
                'Audio quality as Mean Opinion Score, (between 1 and 5)',
                labels=['id']),
            'variable_rtp_audio_rtcp_octet_count': GaugeMetricFamily(
                'rtcp_audio_bytes_total',
                'Total number of rtcp bytes in this channel.',
                labels=['id']),
            'variable_rtp_audio_rtcp_packet_count': GaugeMetricFamily(
                'rtcp_audio_packets_total',
                'Total number of rtcp packets in this channel.',
                labels=['id']),
        }

        channel_info_metric = GaugeMetricFamily(
            'rtp_channel_info',
            'FreeSWITCH RTP channel info',
            labels=['id', 'name', 'user_agent'])

        millisecond_metrics = [
            'variable_rtp_audio_in_jitter_min_variance',
            'variable_rtp_audio_in_jitter_max_variance',
            'variable_rtp_audio_in_mean_interval',
        ]

        # This loop is potentially running while calls are being dropped and
        # new calls are established. This will lead to some failing api
        # requests. In that case it is better to just skip scraping for that
        # call and continue with the next one in order to avoid failing the
        # whole scrape.
        (_, result) = await self._esl.send('api show calls as json')
        for row in json.loads(result).get('rows', []):
            uuid = row['uuid']

            await self._esl.send('api uuid_set_media_stats %s' % (uuid,))
            (_, result) = await self._esl.send('api uuid_dump %s json' % (uuid,))

            if result.startswith("-ERR "):
                self._log.debug(
                    "Got error while scraping call stats for %s: %s",
                    uuid,
                    result.strip()
                )
                continue

            channel_vars = json.loads(result)

            label_values = [uuid]
            for key, metric_value in channel_vars.items():
                if key in millisecond_metrics:
                    metric_value = float(metric_value) / 1000.
                if key in channel_metrics:
                    channel_metrics[key].add_metric(
                        label_values, metric_value)

            user_agent = channel_vars.get('variable_sip_user_agent', 'Unknown')
            channel_info_label_values = [uuid, row['name'], user_agent]
            channel_info_metric.add_metric(
                channel_info_label_values, 1)

        return itertools.chain(
            channel_metrics.values(),
            [channel_info_metric])


class ESLSofiaStatusCollector:
    def __init__(self, esl: ESL):
        self._esl = esl
        self._log = logging.getLogger(__name__)

    async def collect(self):
        gauges = []
        sofia_profile_status_fields = {
            "congestion": GaugeMetricFamily(
                "sofia_profile_congested_calls_total",
                "How many calls were rejected for busy lines or other resource exhaustion on this Sofia profile.",
                labels=["name"],
            ),
            "session_to": GaugeMetricFamily(
                "sofia_profile_session_timeout_total",
                "How many calls were dropped for timeout causes on this Sofia profile.",
                labels=["name"],
            ),
            "max_dialog": GaugeMetricFamily(
                "sofia_profile_maximum_sessions_configuration",
                "How many sessions can be active at once on this Sofia profile before refusing calls for congestion.",
                labels=["name"],
            ),
            "calls_in": GaugeMetricFamily(
                "sofia_profile_calls_inbound_total",
                "How many calls were received inbound on this Sofia profile.",
                labels=["name"],
            ),
            "failed_calls_in": GaugeMetricFamily(
                "sofia_profile_failed_inbound_calls_total",
                "How many incoming calls couldn't be accepted by this Sofia profile.",
                labels=["name"],
            ),
            "calls_out": GaugeMetricFamily(
                "sofia_profile_calls_outbound_total",
                "How many calls were send by this Sofia profile.",
                labels=["name"],
            ),
            "failed_calls_out": GaugeMetricFamily(
                "sofia_profile_failed_outbound_calls_total",
                "How many outbound calls couldn't be completed by this Sofia profile.",
                labels=["name"],
            ),
            "registrations": GaugeMetricFamily(
                "sofia_profile_registrations_total",
                "How many clients are registered to this Sofia profile.",
                labels=["name"],
            ),
        }

        (_, sofia_status_data) = await self._esl.send('api sofia status')

        for profile in SofiaProfile.profile_list_from_sofia_status(sofia_status_data):
            (_, sofia_profile_status_data) = await self._esl.send('api sofia status profile %s' % profile.name)
            sofia_profile_status = SofiaProfileStatus(sofia_profile_status_data)

            for name, gauge in sofia_profile_status_fields.items():
                gauge.add_metric([sofia_profile_status.name], getattr(sofia_profile_status, name))
                gauges.append(gauge)

        return gauges


class ChannelCollector:
    """
    Collects channel statistics.

    # HELP freeswitch_version_info FreeSWITCH version info
    # TYPE freeswitch_version_info gauge
    freeswitch_version_info{release="15",repoid="7599e35a",version="4.4"} 1.0
    """

    def __init__(self, host, port, password):
        self._host = host
        self._port = port
        self._password = password

    def collect(self):  # pylint: disable=missing-docstring
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(self._collect())

    async def _collect(self):
        reader, writer = await asyncio.open_connection(self._host, self._port)
        try:
            esl = ESL(reader, writer)
            await esl.initialize()
            await esl.login(self._password)

            return itertools.chain(
                await ESLProcessInfo(esl).collect(),
                await ESLChannelInfo(esl).collect(),
                await ESLSofiaStatusCollector(esl).collect(),
            )

        finally:
            writer.close()


def collect_esl(config, host):
    """Scrape a host and return prometheus text format for it (async)"""

    port = config.get('port', 8021)
    password = config.get('password', 'ClueCon')

    registry = CollectorRegistry()
    registry.register(ChannelCollector(host, port, password))
    return generate_latest(registry)
