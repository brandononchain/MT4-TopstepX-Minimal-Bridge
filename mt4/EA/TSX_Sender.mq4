##property strict

// ---- Inputs ----
input string BridgeHost = "http://127.0.0.1";
input int    BridgePort = 8787;
input string AccountTag = "default";
input bool   AutoMap    = true;    // bridge maps MT4 symbol → futures
input int    PollSecs   = 1;       // scan frequency (sec)
input int    TimeoutMs  = 4000;    // HTTP timeout

// ---- State ----
int    KnownTickets[];     // open tickets snapshot
double K_Lots[];           // lots per ticket
double K_SL[];             // SL per ticket
double K_TP[];             // TP per ticket
double K_OpenPrice[];      // open price snapshot
int    K_Type[];           // order type snapshot

// ---- Util: request wrapper (matches MQL4 overloads) ----
int HttpRequest(const string method, const string url, const string body_json, string &resp_body, int timeout_ms)
{
   string headers = "Content-Type: application/json\r\n";
   string resp_headers = "";
   int    code = -1;
   char data[], result[];

   if(body_json == "" || StringLen(body_json) == 0)
   {
      ArrayResize(data, 0);
      code = WebRequest(method, url, headers, timeout_ms, data, result, resp_headers);
   }
   else
   {
      StringToCharArray(body_json, data, 0, WHOLE_ARRAY);
      int sz = ArraySize(data);
      if(sz > 0) sz--; // exclude null terminator
      code = WebRequest(method, url, headers, "", timeout_ms, data, sz, result, resp_headers);
   }
   resp_body = CharArrayToString(result);
   return code;
}

void SendIntent(const string eventName, int ticket, const string sym, int type,
                double lots, double price, double sl, double tp, double closePrice=0.0, double profit=0.0)
{
   string side = (type==OP_BUY || type==OP_BUYLIMIT || type==OP_BUYSTOP) ? "BUY" : "SELL";

   // Build JSON (avoid NaNs)
   string payload = StringFormat(
      "{\"event\":\"%s\",\"account_tag\":\"%s\",\"symbol\":\"%s\",\"side\":\"%s\",\"price\":%.5f,\"sl\":%.5f,\"tp\":%.5f,\"ticket\":%d,\"qty\":%.2f,\"close_price\":%.5f,\"profit\":%.2f,\"auto_map\":%s}",
      eventName, AccountTag, sym, side, price, sl, tp, ticket, lots, closePrice, profit, AutoMap ? "true" : "false"
   );

   string url = StringFormat("%s:%d/intent", BridgeHost, BridgePort);
   string resp = "";
   int code = HttpRequest("POST", url, payload, resp, TimeoutMs);
   if(code != 200)
      Print("POST failed(", eventName, ") code=", code, " resp=", resp, " payload=", payload);
   else
      Print("POST ok(", eventName, "): ", resp);
}

// ---- Snapshot helpers ----
int FindTicketIndex(int ticket)
{
   for(int i=0;i<ArraySize(KnownTickets);i++)
      if(KnownTickets[i]==ticket) return i;
   return -1;
}

void UpsertOpenOrderSnapshot(int ticket, int type, double lots, double openPrice, double sl, double tp)
{
   int idx = FindTicketIndex(ticket);
   if(idx<0)
   {
      int n = ArraySize(KnownTickets);
      ArrayResize(KnownTickets, n+1);
      ArrayResize(K_Lots, n+1);
      ArrayResize(K_SL, n+1);
      ArrayResize(K_TP, n+1);
      ArrayResize(K_OpenPrice, n+1);
      ArrayResize(K_Type, n+1);
      idx = n;
      KnownTickets[idx] = ticket;
   }
   K_Lots[idx] = lots;
   K_SL[idx] = sl;
   K_TP[idx] = tp;
   K_OpenPrice[idx] = openPrice;
   K_Type[idx] = type;
}

void RemoveTicket(int ticket)
{
   int idx = FindTicketIndex(ticket);
   if(idx<0) return;
   int last = ArraySize(KnownTickets)-1;
   if(idx != last)
   {
      KnownTickets[idx] = KnownTickets[last];
      K_Lots[idx] = K_Lots[last];
      K_SL[idx] = K_SL[last];
      K_TP[idx] = K_TP[last];
      K_OpenPrice[idx] = K_OpenPrice[last];
      K_Type[idx] = K_Type[last];
   }
   ArrayResize(KnownTickets, last);
   ArrayResize(K_Lots, last);
   ArrayResize(K_SL, last);
   ArrayResize(K_TP, last);
   ArrayResize(K_OpenPrice, last);
   ArrayResize(K_Type, last);
}

// ---- Core scanner: detects OPEN/MODIFY/CLOSE ----
void Scan()
{
   // 1) Check all current open trades for OPEN/MODIFY
   int openCount = OrdersTotal();
   for(int i=0;i<openCount;i++)
   {
      if(!OrderSelect(i, SELECT_BY_POS, MODE_TRADES)) continue;
      int ticket = OrderTicket();
      string sym = OrderSymbol();
      int type   = OrderType();
      double lots= OrderLots();
      double op  = OrderOpenPrice();
      double sl  = OrderStopLoss();
      double tp  = OrderTakeProfit();

      int idx = FindTicketIndex(ticket);
      if(idx<0)
      {
         // NEW OPEN
         SendIntent("open", ticket, sym, type, lots, op, sl, tp, 0.0, 0.0);
         UpsertOpenOrderSnapshot(ticket, type, lots, op, sl, tp);
      }
      else
      {
         // Possible MODIFY
         bool changed = (MathAbs(K_Lots[idx]-lots)>0.0000001) ||
                        (MathAbs(K_SL[idx]-sl)>0.0000001)     ||
                        (MathAbs(K_TP[idx]-tp)>0.0000001);
         if(changed)
         {
            SendIntent("modify", ticket, sym, type, lots, op, sl, tp, 0.0, 0.0);
            UpsertOpenOrderSnapshot(ticket, type, lots, op, sl, tp);
         }
      }
   }

   // 2) Detect CLOSE events: any known ticket not in MODE_TRADES anymore
   //    Confirm in history and emit with close price/profit
   int n = ArraySize(KnownTickets);
   for(int k=n-1;k>=0;k--)
   {
      int t = KnownTickets[k];
      bool stillOpen = false;
      for(int j=0;j<OrdersTotal();j++)
      {
         if(OrderSelect(j, SELECT_BY_POS, MODE_TRADES) && OrderTicket()==t) { stillOpen=true; break; }
      }
      if(!stillOpen)
      {
         // find in history
         double cprice=0, profit=0; string sym="";
         bool foundHist = false;
         int htotal = OrdersHistoryTotal();
         for(int h=htotal-1; h>=0 && !foundHist; h--)
         {
            if(OrderSelect(h, SELECT_BY_POS, MODE_HISTORY) && OrderTicket()==t)
            {
               cprice = OrderClosePrice();
               profit = OrderProfit() + OrderSwap() + OrderCommission();
               sym    = OrderSymbol();
               foundHist = true;
            }
         }
         // use snapshot to recover type/lots/open if needed
         int idx = FindTicketIndex(t);
         int type = (idx>=0 ? K_Type[idx] : OP_BUY);
         double lots = (idx>=0 ? K_Lots[idx] : 0.0);
         double op   = (idx>=0 ? K_OpenPrice[idx] : 0.0);
         double sl   = (idx>=0 ? K_SL[idx] : 0.0);
         double tp   = (idx>=0 ? K_TP[idx] : 0.0);

         SendIntent("close", t, (sym==""?"UNKNOWN":sym), type, lots, op, sl, tp, cprice, profit);
         RemoveTicket(t);
      }
   }
}

// ---- Lifecycle ----
int OnInit()
{
   // Whitelist http://127.0.0.1:8787 in MT4: Tools → Options → Expert Advisors → Allow WebRequest ...
   string url = StringFormat("%s:%d/health", BridgeHost, BridgePort);
   string resp="";
   int code = HttpRequest("GET", url, "", resp, 3000);
   Print("Bridge health code=", code, " resp=", resp);

   ArrayResize(KnownTickets, 0);
   EventSetTimer(PollSecs);      // 1-sec polling for near real-time capture
   return(INIT_SUCCEEDED);
}

void OnTimer()
{
   Scan();
}

void OnDeinit(const int reason)
{
   EventKillTimer();
}
