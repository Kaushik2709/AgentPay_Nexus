import json
import hashlib
import datetime
from sqlalchemy.orm import Session
from app.db.session import sync_engine, SyncSessionLocal, init_db
from app.db.models import Product, Merchant, Policy, AuditEntry

def compute_sha256(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()

def seed_database():
    init_db()
    with SyncSessionLocal() as db:
        # Check if already seeded
        existing_products = db.query(Product).count()
        if existing_products > 0:
            print("[SEED] Database already populated with real catalog data.")
            merchant = db.query(Merchant).filter(Merchant.id == "merchant_techgear_01").first()
            if merchant:
                merchant.margin_floor_pct = 0.20
                db.commit()
            return

        print("[SEED] Seeding real production catalog, merchants, policies, and genesis audit block...")

        products = [
            Product(
                sku="item_monitor_4k_standard",
                name="UltraView 27\" 4K UHD IPS Monitor",
                category="monitors",
                description="27-inch 4K UHD (3840x2160) IPS Display, 60Hz, 99% sRGB, HDR400, Dual HDMI 2.0 & DisplayPort 1.4.",
                specifications=json.dumps({
                    "resolution": "4K (3840x2160)",
                    "refresh_rate": "60Hz",
                    "panel_type": "IPS",
                    "color_gamut": "99% sRGB",
                    "inputs": ["HDMI 2.0", "DisplayPort 1.4"]
                }),
                cost_price=13800.0,
                retail_price=18500.0,
                stock_quantity=15,
                upgrade_to_sku="item_monitor_4k_creator",
                upgrade_bundle_discount=1000.0,
                warranty_price=1200.0,
                json_ld_schema=json.dumps({
                    "@context": "https://schema.org/",
                    "@type": "Product",
                    "name": "UltraView 27\" 4K UHD IPS Monitor",
                    "sku": "item_monitor_4k_standard",
                    "brand": "UltraView",
                    "offers": {
                        "@type": "Offer",
                        "priceCurrency": "INR",
                        "price": 18500.0,
                        "availability": "https://schema.org/InStock"
                    }
                }),
                is_subscription=False
            ),
            Product(
                sku="item_monitor_4k_creator",
                name="UltraView Creator Pro 27\" 4K 120Hz Mini-LED Monitor",
                category="monitors",
                description="27-inch 4K UHD (3840x2160) 120Hz Mini-LED display with 576 local dimming zones, 99% DCI-P3, USB-C 90W PD.",
                specifications=json.dumps({
                    "resolution": "4K (3840x2160)",
                    "refresh_rate": "120Hz",
                    "panel_type": "Mini-LED",
                    "color_gamut": "99% DCI-P3",
                    "inputs": ["USB-C 90W PD", "HDMI 2.1", "DisplayPort 1.4"]
                }),
                cost_price=16000.0,
                retail_price=21000.0,
                stock_quantity=12,
                warranty_price=1500.0,
                json_ld_schema=json.dumps({
                    "@context": "https://schema.org/",
                    "@type": "Product",
                    "name": "UltraView Creator Pro 27\" 4K 120Hz Mini-LED Monitor",
                    "sku": "item_monitor_4k_creator",
                    "brand": "UltraView",
                    "offers": {
                        "@type": "Offer",
                        "priceCurrency": "INR",
                        "price": 21000.0,
                        "availability": "https://schema.org/InStock"
                    }
                }),
                is_subscription=False
            ),
            Product(
                sku="item_keyboard_ergo",
                name="ErgoType Split Mechanical Keyboard",
                category="keyboards",
                description="Ergonomic split design with hot-swappable Gateron Brown tactile switches, PBT keycaps, and dual-mode wireless 2.4G/BT.",
                specifications=json.dumps({
                    "layout": "Split 75%",
                    "switch_type": "Gateron Brown Tactile",
                    "connectivity": "Wireless 2.4GHz + Bluetooth 5.2 + USB-C",
                    "battery": "4000mAh (Up to 200 hours)"
                }),
                cost_price=3100.0,
                retail_price=4500.0,
                stock_quantity=25,
                upgrade_to_sku="item_keyboard_pro",
                upgrade_bundle_discount=500.0,
                warranty_price=499.0,
                json_ld_schema=json.dumps({
                    "@context": "https://schema.org/",
                    "@type": "Product",
                    "name": "ErgoType Split Mechanical Keyboard",
                    "sku": "item_keyboard_ergo",
                    "brand": "ErgoType",
                    "offers": {
                        "@type": "Offer",
                        "priceCurrency": "INR",
                        "price": 4500.0,
                        "availability": "https://schema.org/InStock"
                    }
                }),
                is_subscription=False
            ),
            Product(
                sku="item_keyboard_pro",
                name="ErgoType Pro CNC Aluminium Alice Keyboard",
                category="keyboards",
                description="CNC Anodized Aluminium Alice layout with custom lubed linear switches, gasket mount, sound dampening foam, and OLED screen.",
                specifications=json.dumps({
                    "layout": "Alice Ergonomic",
                    "body": "CNC Anodized Aluminum 6063",
                    "switch_type": "Custom Factory-Lubed Linear 45g",
                    "mount": "Gasket Mount with Poron Dampeners"
                }),
                cost_price=4600.0,
                retail_price=6500.0,
                stock_quantity=8,
                warranty_price=699.0,
                json_ld_schema=json.dumps({
                    "@context": "https://schema.org/",
                    "@type": "Product",
                    "name": "ErgoType Pro CNC Aluminium Alice Keyboard",
                    "sku": "item_keyboard_pro",
                    "brand": "ErgoType",
                    "offers": {
                        "@type": "Offer",
                        "priceCurrency": "INR",
                        "price": 6500.0,
                        "availability": "https://schema.org/InStock"
                    }
                }),
                is_subscription=False
            ),
            Product(
                sku="item_mouse_ergo",
                name="MasterGrip Precision Ergonomic Wireless Mouse",
                category="mice",
                description="Vertical 57-degree natural handshake angle, 4000 DPI Darkfield sensor, silent switches, and hyper-fast mag-scroll wheel.",
                specifications=json.dumps({
                    "angle": "57-degree vertical ergonomic",
                    "dpi": "400 to 4000 DPI adjustable",
                    "clicks": "Acoustic Dampened Silent Switches",
                    "battery": "USB-C Fast Rechargeable"
                }),
                cost_price=1450.0,
                retail_price=2200.0,
                stock_quantity=30,
                warranty_price=299.0,
                json_ld_schema=json.dumps({
                    "@context": "https://schema.org/",
                    "@type": "Product",
                    "name": "MasterGrip Precision Ergonomic Wireless Mouse",
                    "sku": "item_mouse_ergo",
                    "brand": "MasterGrip",
                    "offers": {
                        "@type": "Offer",
                        "priceCurrency": "INR",
                        "price": 2200.0,
                        "availability": "https://schema.org/InStock"
                    }
                }),
                is_subscription=False
            ),
            Product(
                sku="item_desk_mat",
                name="EcoLeather XL Desk Mat & Cable Organizer",
                category="accessories",
                description="90x40cm premium micro-textured vegan leather desk pad with anti-slip suede base and magnetic cable routing module.",
                specifications=json.dumps({
                    "dimensions": "90cm x 40cm x 2mm",
                    "material": "Water-resistant Vegan PU Leather",
                    "features": ["Magnetic cable snap", "Anti-fray stitched edges"]
                }),
                cost_price=420.0,
                retail_price=799.0,
                stock_quantity=50,
                warranty_price=99.0,
                json_ld_schema=json.dumps({
                    "@context": "https://schema.org/",
                    "@type": "Product",
                    "name": "EcoLeather XL Desk Mat & Cable Organizer",
                    "sku": "item_desk_mat",
                    "brand": "TechGear",
                    "offers": {
                        "@type": "Offer",
                        "priceCurrency": "INR",
                        "price": 799.0,
                        "availability": "https://schema.org/InStock"
                    }
                }),
                is_subscription=False
            ),
            Product(
                sku="item_usb_c_hub",
                name="MultiPort 8-in-1 Aluminum USB-C Hub",
                category="accessories",
                description="Dual 4K 60Hz HDMI, 100W USB-C Power Delivery pass-through, 3x USB 3.2 Gen 2 (10Gbps), Gigabit Ethernet, SD/TF reader.",
                specifications=json.dumps({
                    "ports": "2x HDMI (4K@60Hz), 1x USB-C 100W PD, 3x USB-A 3.2, 1x RJ45 1Gbps, 1x SD/MicroSD",
                    "chassis": "Space Gray Aluminum"
                }),
                cost_price=1200.0,
                retail_price=1899.0,
                stock_quantity=35,
                warranty_price=250.0,
                json_ld_schema=json.dumps({
                    "@context": "https://schema.org/",
                    "@type": "Product",
                    "name": "MultiPort 8-in-1 Aluminum USB-C Hub",
                    "sku": "item_usb_c_hub",
                    "brand": "TechGear",
                    "offers": {
                        "@type": "Offer",
                        "priceCurrency": "INR",
                        "price": 1899.0,
                        "availability": "https://schema.org/InStock"
                    }
                }),
                is_subscription=False
            ),
            Product(
                sku="item_coffee_beans_subscription",
                name="Coorg Single-Origin Specialty Arabica Beans (1kg/mo)",
                category="subscriptions",
                description="Medium-dark roast shade-grown artisan coffee beans from Coorg with notes of dark chocolate and roasted hazelnut. Monthly delivery mandate.",
                specifications=json.dumps({
                    "origin": "Coorg, Karnataka, India (Altitude: 1200m)",
                    "roast": "Medium-Dark Artisan",
                    "frequency": "Monthly automated replenishment",
                    "quantity": "1000g whole beans"
                }),
                cost_price=550.0,
                retail_price=1100.0,
                stock_quantity=100,
                warranty_price=0.0,
                json_ld_schema=json.dumps({
                    "@context": "https://schema.org/",
                    "@type": "Product",
                    "name": "Coorg Single-Origin Specialty Arabica Beans (1kg/mo)",
                    "sku": "item_coffee_beans_subscription",
                    "brand": "EstateCraft",
                    "offers": {
                        "@type": "Offer",
                        "priceCurrency": "INR",
                        "price": 1100.0,
                        "availability": "https://schema.org/InStock"
                    }
                }),
                is_subscription=True
            ),
            Product(
                sku="item_cloud_credits_subscription",
                name="DevStack AI Inference GPU Cloud Pack (Monthly)",
                category="subscriptions",
                description="500 Compute Units of Dedicated H100 GPU inference for autonomous AI agent pipelines with low-latency endpoints.",
                specifications=json.dumps({
                    "compute_units": "500 GPU Hours",
                    "hardware": "NVIDIA H100 SXM5",
                    "billing": "Recurring Monthly Mandate via UPI Autopay"
                }),
                cost_price=1750.0,
                retail_price=2999.0,
                stock_quantity=999,
                warranty_price=0.0,
                json_ld_schema=json.dumps({
                    "@context": "https://schema.org/",
                    "@type": "Product",
                    "name": "DevStack AI Inference GPU Cloud Pack (Monthly)",
                    "sku": "item_cloud_credits_subscription",
                    "brand": "DevStack Cloud",
                    "offers": {
                        "@type": "Offer",
                        "priceCurrency": "INR",
                        "price": 2999.0,
                        "availability": "https://schema.org/InStock"
                    }
                }),
                is_subscription=True
            ),
            Product(
                sku="item_limited_stock_headset",
                name="StudioMaster Pro ANC Wireless Studio Headphones",
                category="electronics",
                description="40mm Beryllium dynamic drivers, active hybrid noise cancellation, LDAC 24-bit Hi-Res audio, and 45-hour battery life. Limited inventory item.",
                specifications=json.dumps({
                    "drivers": "40mm Custom Beryllium",
                    "anc": "-42dB Hybrid Active Noise Cancellation",
                    "codecs": ["LDAC", "aptX HD", "AAC", "SBC"],
                    "battery": "45 Hours ANC On"
                }),
                cost_price=6800.0,
                retail_price=9999.0,
                stock_quantity=1,  # Stock 1 to showcase stock depletion / race condition
                warranty_price=899.0,
                json_ld_schema=json.dumps({
                    "@context": "https://schema.org/",
                    "@type": "Product",
                    "name": "StudioMaster Pro ANC Wireless Studio Headphones",
                    "sku": "item_limited_stock_headset",
                    "brand": "StudioMaster",
                    "offers": {
                        "@type": "Offer",
                        "priceCurrency": "INR",
                        "price": 9999.0,
                        "availability": "https://schema.org/InStock"
                    }
                }),
                is_subscription=False
            ),
            Product(
                sku="item_motherboard_gigabyte_elite",
                name="GIGABYTE Z790 AORUS Elite AX Motherboard",
                category="electronics",
                description="Intel LGA1700 ATX Motherboard, Twin 16+1+2 Digital VRM, DDR5 7600MHz OC, PCIe 5.0, 4x M.2 Thermal Guard, Wi-Fi 6E & 2.5GbE LAN.",
                specifications=json.dumps({
                    "socket": "LGA1700 (Intel 14th/13th/12th Gen)",
                    "memory": "4x DDR5 DIMM up to 192GB, 7600MHz OC",
                    "pcie": "1x PCIe 5.0 x16, 2x PCIe 4.0 x4",
                    "storage": "4x M.2 PCIe 4.0 NVMe with heatsinks",
                    "networking": "Intel Wi-Fi 6E + 2.5GbE Realtek LAN",
                    "form_factor": "ATX"
                }),
                cost_price=19000.0,
                retail_price=24500.0,
                stock_quantity=10,
                upgrade_to_sku="item_motherboard_gigabyte_master",
                upgrade_bundle_discount=2500.0,
                warranty_price=1499.0,
                json_ld_schema=json.dumps({
                    "@context": "https://schema.org/",
                    "@type": "Product",
                    "name": "GIGABYTE Z790 AORUS Elite AX Motherboard",
                    "sku": "item_motherboard_gigabyte_elite",
                    "brand": "GIGABYTE",
                    "offers": {
                        "@type": "Offer",
                        "priceCurrency": "INR",
                        "price": 24500.0,
                        "availability": "https://schema.org/InStock"
                    }
                }),
                is_subscription=False
            ),
            Product(
                sku="item_motherboard_gigabyte_master",
                name="GIGABYTE Z790 AORUS Master Xtreme Gaming Motherboard",
                category="electronics",
                description="Flagship E-ATX Motherboard, Direct 20+1+2 VRM with 105A Power Stages, DDR5 8000MHz OC, PCIe 5.0 M.2 EZ-Latch, 10GbE Aquantia LAN & Wi-Fi 7.",
                specifications=json.dumps({
                    "socket": "LGA1700 (Intel 14th/13th Gen Extreme)",
                    "memory": "4x DDR5 DIMM up to 192GB, 8000MHz OC",
                    "pcie": "1x PCIe 5.0 x16, 5x M.2 (1x Gen 5.0 + 4x Gen 4.0)",
                    "networking": "Marvell AQtion 10GbE LAN + Intel Wi-Fi 7",
                    "form_factor": "E-ATX Flagship"
                }),
                cost_price=33000.0,
                retail_price=42000.0,
                stock_quantity=6,
                warranty_price=2499.0,
                json_ld_schema=json.dumps({
                    "@context": "https://schema.org/",
                    "@type": "Product",
                    "name": "GIGABYTE Z790 AORUS Master Xtreme Gaming Motherboard",
                    "sku": "item_motherboard_gigabyte_master",
                    "brand": "GIGABYTE",
                    "offers": {
                        "@type": "Offer",
                        "priceCurrency": "INR",
                        "price": 42000.0,
                        "availability": "https://schema.org/InStock"
                    }
                }),
                is_subscription=False
            )
        ]

        db.add_all(products)

        # Seed Merchant
        merchant = Merchant(
            id="merchant_techgear_01",
            name="TechGear India (Official Store)",
            margin_floor_pct=0.20,
            active_growth_models=json.dumps(["quality_upgrade", "conversion_closer", "bulk_subscription", "value_services"]),
            api_key="sec_live_merchant_nexus_991823"
        )
        db.add(merchant)

        # Seed Buyer Policy
        policy = Policy(
            id="policy_default_user",
            user_id="aarav_buyer_01",
            max_tx_amount=25000.0,
            daily_velocity_cap=50000.0,
            category_whitelist=json.dumps(["monitors", "keyboards", "mice", "electronics", "accessories", "furniture", "subscriptions", "services"]),
            allow_autonomous_upsell=False,
            price_drift_tolerance_pct=3.0
        )
        db.add(policy)

        # Seed Genesis Audit Block
        genesis_payload_dict = {
            "event": "GENESIS_LEDGER_INITIALIZATION",
            "message": "Cryptographic Audit Ledger Initialized with SHA-256 Chaining",
            "protocol": "AgentPay_Nexus_ACP_v1.1"
        }
        genesis_payload = json.dumps(genesis_payload_dict, sort_keys=True)
        genesis_prev = "0000000000000000000000000000000000000000000000000000000000000000"
        genesis_timestamp = datetime.datetime.utcnow().isoformat()
        
        # Format identical to AuditLedgerEngine: sequence|actor|action|timestamp|prev_hash|payload_json
        genesis_raw = f"0|SYSTEM|GENESIS_INITIALIZATION|{genesis_timestamp}|{genesis_prev}|{genesis_payload}"
        genesis_hash = compute_sha256(genesis_raw)

        genesis_entry = AuditEntry(
            sequence_number=0,
            timestamp=genesis_timestamp,
            actor="SYSTEM",
            action="GENESIS_INITIALIZATION",
            payload_json=genesis_payload,
            prev_hash=genesis_prev,
            entry_hash=genesis_hash,
            verified=True
        )
        db.add(genesis_entry)

        db.commit()
        print("[SEED] Seed data successfully committed.")

if __name__ == "__main__":
    seed_database()
