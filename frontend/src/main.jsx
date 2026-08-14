/*
 * Copyright © 2026 Paradigm Strategic Partners, LLC.
 * All Rights Reserved.
 *
 * Paradigm Training Manager™ is proprietary and confidential software.
 * Unauthorized copying, modification, distribution, or use is prohibited.
 * Software ID: PTM-PSP-2026
 */

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import App from "./App.jsx";

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <App />
  </StrictMode>
);
