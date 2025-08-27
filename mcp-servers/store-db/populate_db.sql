-- Sample data for the products table

INSERT INTO products (name, description, inventory, price) VALUES
('Super Widget', 'A high-quality widget with advanced features and a sleek design.', 100, 29.99),
('Mega Gadget', 'The latest gadget that everyone is talking about. Packed with power.', 50, 79.50),
('Awesome Gizmo', 'A versatile gizmo for all your daily needs. Simple and effective.', 200, 12.75),
('Hyper Doodad', 'Experience the next level of doodads with this hyper-efficient model.', 75, 45.00),
('Ultra Thingamajig', 'The ultimate thingamajig, built for performance and durability.', 120, 99.99),
('Quantum Sprocket', 'A revolutionary sprocket utilizing quantum technology for unparalleled precision.', 30, 199.00),
('Stealth Frob', 'A discreet frob that gets the job done without drawing attention.', 150, 22.50),
('Cosmic Ratchet', 'A ratchet powerful enough to tighten bolts across galaxies. (Metaphorically)', 60, 65.20),
('Zenith Component', 'The pinnacle of component design, offering superior integration.', 90, 33.80),
('Nova Fastener', 'A new-age fastener that promises a secure hold every time.', 250, 5.95);

-- Note: The 'orders' table will be populated as orders are made through the API.
-- The 'id' columns are auto-incrementing primary keys and should not be specified in INSERT statements
-- unless you are intentionally setting them and have handled sequence adjustments.
