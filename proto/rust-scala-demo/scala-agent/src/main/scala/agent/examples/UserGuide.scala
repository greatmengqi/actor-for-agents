package agent.examples

import agent.actor.*
import agent.pb.agent.OnExhaust

// ══════════════════════════════════════════════════════════════
// 用户接入指南
//
// 无状态 actor:  extends Actor
//   def receive(msg)(using ctx): String
//
// 有状态 actor:  extends StatefulActor[S]
//   def receive(msg, state)(using ctx): (String, S)
//   状态自动加载/保存，你不碰 load/save
// ══════════════════════════════════════════════════════════════

// ─────────────────────────────────────────────
// Level 1: 最简 — 无状态，一个 ask
// ─────────────────────────────────────────────

object TranslatorExample extends Actor:
  private val llm = ActorRef[String]("llm_actor")

  def receive(msg: String)(using ctx: ActorContext): String =
    llm.ask(s"Translate to English: $msg")

// ─────────────────────────────────────────────
// Level 2: 有状态 — 待办清单
// ─────────────────────────────────────────────

case class TodoState(items: List[String] = Nil)

object TodoListExample extends StatefulActor[TodoState]:
  def initial = TodoState()
  def encode(s: TodoState) = s.items.mkString("\n")
  def decode(raw: String) = TodoState(if raw.isEmpty then Nil else raw.split("\n").toList)

  def receive(msg: String, state: TodoState)(using ctx: ActorContext): (String, TodoState) =
    msg.split(" ", 2) match
      case Array("add", task) =>
        val next = state.copy(items = state.items :+ task)
        (s"Added: $task (total: ${next.items.size})", next)

      case Array("list") =>
        val text = if state.items.isEmpty then "No todos"
                   else state.items.zipWithIndex.map((t, i) => s"  ${i + 1}. $t").mkString("\n")
        (text, state)  // list 不改状态

      case Array("done", idx) =>
        val i = idx.toInt - 1
        if i < 0 || i >= state.items.size then (s"Invalid index: $idx", state)
        else
          val removed = state.items(i)
          val next = state.copy(items = state.items.patch(i, Nil, 1))
          (s"Done: $removed (remaining: ${next.items.size})", next)

      case _ => ("Usage: add <task> | list | done <n>", state)

// ─────────────────────────────────────────────
// Level 3: 流式输出 — Code Reviewer
// ─────────────────────────────────────────────

object CodeReviewerExample extends Actor:
  private val llm = ActorRef[String]("llm_actor")

  def receive(msg: String)(using ctx: ActorContext): String =
    ctx.emit("Analyzing code structure...")
    val structure = llm.ask(s"Analyze the structure of:\n$msg")

    ctx.emit("Checking for bugs...")
    val bugs = llm.ask(s"Find bugs in:\n$msg")

    ctx.emit("Suggesting improvements...")
    val improvements = llm.ask(s"Suggest improvements for:\n$msg")

    ctx.emit("Compiling review report...")
    s"## Structure\n$structure\n\n## Bugs\n$bugs\n\n## Improvements\n$improvements"

// ─────────────────────────────────────────────
// Level 4: 并行 — 比价
// ─────────────────────────────────────────────

object PriceCompareExample extends Actor:
  private val supplierA = ActorRef[String]("supplier_a")
  private val supplierB = ActorRef[String]("supplier_b")
  private val supplierC = ActorRef[String]("supplier_c")
  private val llm       = ActorRef[String]("llm_actor")

  def receive(msg: String)(using ctx: ActorContext): String =
    ctx.emit(s"Querying 3 suppliers for '$msg'...")
    val results = ctx.askAll(supplierA -> s"price:$msg", supplierB -> s"price:$msg", supplierC -> s"price:$msg")
    ctx.emit("Comparing prices...")
    llm.ask(s"Which is cheapest? $results")

// ─────────────────────────────────────────────
// Level 5: 组合 — 招聘（状态 + 并行 + 流式 + 容错）
// ─────────────────────────────────────────────

case class RecruitState(evaluations: Int = 0, lastResult: String = "")

object RecruiterExample extends StatefulActor[RecruitState]:
  private val techEval = ActorRef[String]("tech_evaluator")
  private val culture  = ActorRef[String]("culture_fit")
  private val bgCheck  = ActorRef[String]("background_check")
  private val llm      = ActorRef[String]("llm_actor")
  private val hr       = ActorRef[String]("hr_team")

  def initial = RecruitState()
  def encode(s: RecruitState) = s"${s.evaluations}|${s.lastResult}"
  def decode(raw: String) =
    raw.split("\\|", 2) match
      case Array(n, r) => RecruitState(n.toInt, r)
      case _ => RecruitState()

  def receive(msg: String, state: RecruitState)(using ctx: ActorContext): (String, RecruitState) =
    ctx.withPolicy(maxRetries = 3)
    ctx.emit(s"Evaluation #${state.evaluations + 1} for: $msg")

    val assessments = ctx.askAll(
      techEval -> s"Evaluate skills for '$msg'",
      culture  -> s"Check culture fit",
      bgCheck  -> s"Verify background"
    )

    ctx.emit("All assessments complete, generating recommendation...")
    val recommendation = llm.ask(s"Should we hire?\n$assessments")

    hr.tell(s"Evaluation complete for $msg")

    (recommendation, RecruitState(state.evaluations + 1, recommendation))

// ─────────────────────────────────────────────
// 注册
// ─────────────────────────────────────────────

object ExampleRegistry:
  def registerAll(): Unit =
    ActorSystem.register("translator_ex", TranslatorExample)
    ActorSystem.register("todo_ex", TodoListExample)
    ActorSystem.register("code_reviewer_ex", CodeReviewerExample)
    ActorSystem.register("price_compare_ex", PriceCompareExample)
    ActorSystem.register("recruiter_ex", RecruiterExample)
