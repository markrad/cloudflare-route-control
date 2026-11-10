class CloudflareHostsCard extends HTMLElement {
    constructor() {
        super();
        this.attachShadow({ mode: "open" });
        this._expandedGroups = {};
    }

    setConfig(config) {
        this.config = config;
    }

    set hass(hass) {
        this._hass = hass;
        this.render();
    }

    toggleGroup(groupName) {
        this._expandedGroups[groupName] =
            !this._expandedGroups[groupName];

        this.render();
    }

    showMoreInfo(entityId) {
        this.dispatchEvent(
            new CustomEvent("hass-more-info", {
                bubbles: true,
                composed: true,
                detail: {
                    entityId,
                },
            })
        );
    }

    // async toggleEntity(entityId, enabled) {
    //     await this._hass.callService(
    //         "input_boolean",
    //         enabled ? "turn_on" : "turn_off",
    //         {
    //             entity_id: entityId,
    //         }
    //     );
    // }
    async setRoute(host, entityId, service, enabled) {
        await this._hass.callService(
            "script",
            "set_cloudflare_route",
            {
                host,
                state: enabled ? "on" : "off",
                service,
                entity_id: entityId,
            }
        );
    }
    render() {
        if (!this._hass || !this.config) {
            return;
        }

        const entityId =
            this.config.entity ?? "sensor.cloudflare_managed_hosts";

        const stateObj = this._hass.states[entityId];

        if (!stateObj) {
            this.shadowRoot.innerHTML = `
                <ha-card header="Cloudflare Routes">
                    <div class="error">
                        Entity not found: ${entityId}
                    </div>
                </ha-card>
            `;
            return;
        }

        const categories =
            stateObj.attributes.categories || {};

        const style = `
            <style>
                :host {
                    display: block;
                }

                .section {
                    border-top: 1px solid var(--divider-color);
                }

                .section:first-of-type {
                    border-top: none;
                }

                .section-header {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    padding: 10px 16px;
                    cursor: pointer;
                    user-select: none;
                    background: var(--secondary-background-color);
                    font-weight: 600;
                }

                .section-header:hover {
                    background: var(--table-row-alternative-background-color,
                        rgba(127,127,127,0.08));
                }

                .chevron {
                    transition: transform 0.2s;
                }

                .chevron.expanded {
                    transform: rotate(90deg);
                }

                .host-row {
                  display: flex;
                  align-items: center;
                  gap: 12px;
                  min-height: 48px;
                  padding: 10px 16px;
                  border-left: 4px solid transparent;
                  cursor: pointer;                
                }

                .host-row:hover {
                    background: rgba(127,127,127,0.08);
                }

                .host-row.enabled {
                    border-left-color: var(
                        --success-color,
                        #43a047
                    );
                }

                .host-info {
                    display: flex;
                    flex-direction: column;
                    overflow: hidden;
                }

                .host-title {
                    font-size: 14px;
                    font-weight: 500;
                    color: var(--primary-text-color);
                }

                .host-subtitle {
                    font-size: 12px;
                    color: var(--secondary-text-color);
                    margin-top: 2px;
                }

                .host-service {
                    font-size: 11px;
                    color: var(--secondary-text-color);
                    opacity: 0.8;
                    margin-top: 2px;
                    font-family: monospace;
                }

                .switch-container {
                    margin-left: auto;
                }

                .empty {
                    padding: 16px;
                }

                .error {
                    padding: 16px;
                    color: var(--error-color);
                }
            </style>
        `;

        let body = "";
        for (const [groupName, hosts] of Object.entries(categories)) {
            const expanded =
                this._expandedGroups[groupName] ?? true;

            body += `
                <div class="section">
                    <div class="section-header"
                        data-group="${groupName}">
                        <ha-icon
                            class="chevron ${expanded ? "expanded" : ""}"
                            icon="mdi:chevron-right">
                        </ha-icon>
                        <span>${groupName}</span>
                    </div>
            `;

            if (expanded) {
                for (const [hostName, attributes] of Object.entries(hosts)) {
                    const booleanState =
                        this._hass.states[attributes.entity_id];

                    const enabled =
                        booleanState?.state === "on";

                    const friendlyName =
                        booleanState?.attributes
                            ?.friendly_name || hostName;

                    body += `
                        <div
                            class="host-row ${
                                enabled ? "enabled" : ""
                            }"
                            data-entity="${attributes.entity_id}">

                            <div class="host-info">
                                <div class="host-title">
                                    ${friendlyName}
                                </div>
                                <div class="host-subtitle">
                                    ${hostName}
                                </div>
                                <div class="host-service">
                                    ${attributes.service}
                                </div>
                            </div>

                            <div class="switch-container">
                                <ha-switch
                                    data-toggle="${attributes.entity_id}"
                                    data-host="${hostName}"
                                    data-service="${attributes.service}"
                                    ${
                                        enabled
                                            ? "checked"
                                            : ""
                                    }>
                                </ha-switch>
                            </div>
                        </div>
                    `;
                }
            }

            body += `</div>`;
        }

        this.shadowRoot.innerHTML = `
            ${style}

            <ha-card header="Cloudflare Managed Hosts">
                ${body}
            </ha-card>
        `;

        this.shadowRoot
            .querySelectorAll(".section-header")
            .forEach((header) => {
                header.addEventListener("click", () => {
                    this.toggleGroup(
                        header.dataset.group
                    );
                });
            });

        this.shadowRoot
            .querySelectorAll(".host-row")
            .forEach((row) => {
                row.addEventListener("click", (e) => {
                    if (
                        e.target.tagName.toLowerCase() ===
                        "ha-switch"
                    ) {
                        return;
                    }

                    this.showMoreInfo(
                        row.dataset.entity
                    );
                });
            });

        this.shadowRoot
            .querySelectorAll("ha-switch")
            .forEach((toggle) => {
                toggle.addEventListener(
                    "change",
                    (e) => {
                        e.stopPropagation();

                        this.setRoute(
                            toggle.dataset.host,
                            toggle.dataset.toggle,
                            toggle.dataset.service,
                            toggle.checked
                        );
                    }
                );
            });
    }

    getCardSize() {
        return 6;
    }

    static getStubConfig() {
        return {
            entity: "sensor.cloudflare_managed_hosts",
        };
    }
}

customElements.define(
    "cloudflare-hosts-card",
    CloudflareHostsCard
);