package agent.actor

// ══════════════════════════════════════════════════════════════
// 内置 Actor 示例
//
// 无状态:   extends Actor          → receive(msg)
// 有状态:   extends StatefulActor  → receive(msg, state) => (result, newState)
// ══════════════════════════════════════════════════════════════

// ── 无状态: LLM 代理 ──

object LlmActor extends Actor:
  def receive(msg: String)(using ctx: ActorContext): String =
    ctx.emit(s"[LLM] Processing...")
    ctx.raw.effect(agent.AgentOp.Ask("llm_api", msg))

// ── 有状态: 聊天助手 ──

case class ChatState(history: String = "", messageCount: Int = 0)

object ChatActor extends StatefulActor[ChatState]:
  private val llm   = ActorRef[String]("llm_actor")
  private val audit = ActorRef[String]("audit_actor")

  def initial = ChatState()
  def encode(s: ChatState) = s"${s.messageCount}\n${s.history}"
  def decode(raw: String) =
    val i = raw.indexOf('\n')
    if i < 0 then ChatState() else ChatState(raw.substring(i + 1), raw.substring(0, i).toInt)

  def receive(msg: String, state: ChatState)(using ctx: ActorContext): (String, ChatState) =
    val prompt = if state.history.isEmpty then s"User: $msg"
                 else s"${state.history}\nUser: $msg"

    ctx.emit(s"Thinking... (message #${state.messageCount + 1})")
    val response = llm.ask(prompt)

    ctx.emit("Saving conversation...")
    audit.tell(s"processed:$msg")

    val newState = ChatState(
      history = s"$prompt\nAssistant: $response",
      messageCount = state.messageCount + 1
    )
    (response, newState)

// ── 无状态: 审计日志 ──

object AuditActor extends Actor:
  def receive(msg: String)(using ctx: ActorContext): String =
    ctx.emit(s"[Audit] $msg")
    "logged"

// ── 无状态: 研究员 (parallel + streaming) ──

object ResearcherActor extends Actor:
  private val sourceA = ActorRef[String]("source_a_actor")
  private val sourceB = ActorRef[String]("source_b_actor")
  private val sourceC = ActorRef[String]("source_c_actor")
  private val llm     = ActorRef[String]("llm_actor")

  def receive(msg: String)(using ctx: ActorContext): String =
    ctx.emit(s"Researching '$msg' from 3 sources...")
    val combined = ctx.askAll(sourceA -> msg, sourceB -> msg, sourceC -> msg)
    ctx.emit("Summarizing results...")
    llm.ask(s"Summarize: $combined")

// ── 有状态: 支付 (supervision) ──

case class PaymentState(status: String = "pending", attempts: Int = 0)

object PaymentActor extends StatefulActor[PaymentState]:
  def initial = PaymentState()
  def encode(s: PaymentState) = s"${s.status}|${s.attempts}"
  def decode(raw: String) =
    raw.split("\\|") match
      case Array(st, att) => PaymentState(st, att.toInt)
      case _ => PaymentState()

  def receive(msg: String, state: PaymentState)(using ctx: ActorContext): (String, PaymentState) =
    ctx.withPolicy(maxRetries = 5)
    ctx.emit(s"Processing payment (previous: ${state.status})...")

    val gateway = ctx.actorRef[String]("payment_gateway")
    val result = gateway.ask(s"charge:$msg")

    (result, PaymentState("completed", state.attempts + 1))

// ── 注册 ──

object ActorRegistry:
  def registerAll(): Unit =
    ActorSystem.register("llm_actor", LlmActor)
    ActorSystem.register("audit_actor", AuditActor)
    ActorSystem.register("chat_actor", ChatActor)
    ActorSystem.register("researcher_actor", ResearcherActor)
    ActorSystem.register("payment_actor", PaymentActor)
