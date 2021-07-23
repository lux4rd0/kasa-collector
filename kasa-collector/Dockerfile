FROM grafana/promtail:2.2.1

RUN apt-get update && apt-get install -y bash bc coreutils curl dumb-init jq net-tools procps python python3 sysstat vim

RUN mkdir /kasa-collector

COPY start.sh \
tplink_smartplug.py \
/kasa-collector/

WORKDIR /kasa-collector

RUN chmod a+x *.sh
RUN chmod a+x *.py

ENTRYPOINT ["/usr/bin/dumb-init", "--"]

CMD ["/kasa-collector/start.sh"]
