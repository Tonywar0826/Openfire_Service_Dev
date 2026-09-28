# Openfire 5.1.2 — 从官方 tar.gz 构建（独立 postgres 实例，故障隔离）
# base 用 eclipse-temurin:17-jre（Openfire 5.x 需 Java 17+）
# tar.gz 自带 postgresql-42.7.12.jar 驱动，无需额外 COPY
FROM eclipse-temurin:17-jre

# 创建 openfire 运行用户
RUN useradd -r -m -d /opt/openfire -s /bin/bash openfire

# 解压 Openfire（tar.gz 顶层是 openfire/，--strip-components=1 去掉）
COPY openfire_5_1_2.tar.gz /tmp/openfire.tar.gz
RUN mkdir -p /opt/openfire && \
    tar -xzf /tmp/openfire.tar.gz -C /opt/openfire --strip-components=1 && \
    rm /tmp/openfire.tar.gz && \
    chmod +x /opt/openfire/bin/openfire.sh /opt/openfire/bin/openfirectl && \
    chown -R openfire:openfire /opt/openfire

USER openfire
WORKDIR /opt/openfire

EXPOSE 3478/tcp 3479/tcp 5222/tcp 5223/tcp 5269/tcp 5275/tcp 5276/tcp 7070/tcp 7443/tcp 7777/tcp 9090/tcp 9091/tcp

ENTRYPOINT ["/opt/openfire/bin/openfire.sh"]
