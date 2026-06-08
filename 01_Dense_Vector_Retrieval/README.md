<p align = "center" draggable="false" ><img src="https://github.com/AI-Maker-Space/LLM-Dev-101/assets/37101144/d1343317-fa2f-41e1-8af1-1dbb18399719"
     width="200px"
     height="auto"/>
</p>

<h1 align="center" id="heading">Session 1: Dense Vector Retrieval</h1>

### [Quicklinks]()

| 📰 Module Sheet                                                                 | ⏺️ Recording | 🖼️ Slides | 👨‍💻 Repo       | 📝 Homework | 📁 Feedback |
| :------------------------------------------------------------------------------- | :----------- | :-------- | :------------ | :---------- | :---------- |
| [Dense Vector Retrieval](../00_Docs/Modules/01_Dense_Vector_Retrieval/README.md) |[Recording!](https://us02web.zoom.us/rec/share/sHWvo0Nd1aI0SEhKecOLEX9kFGVJJAdYfsKiuTmm8t85W48Z2lnjpnzTy8jAd8R5.PwuqibGwAZhvDd8c) <br> passcode: `C62n^@Q!`| [Session 1 Slides](https://canva.link/htfqf8i39yejyhn) | You are here! | [Session 1 Assignment](https://forms.gle/Z9qskfVaAvPjn6gz8) | [Feedback 6/2](https://forms.gle/21a2uoL9DVZPwgJP6) |


## 🏗️ How AIM Does Assignments

> 📅 **Assignments will always be released to students as live class begins.** We will never release assignments early.

Each assignment will have a few of the following categories of exercises:

- ❓ **Questions** - these will be questions that you will be expected to gather the answer to. These can appear as general questions, or questions meant to spark a discussion in your breakout rooms.

- 🏗️ **Activities** - these will be work or coding activities meant to reinforce specific concepts or theory components.

- 🚧 **Advanced Builds (optional)** - Take on a challenge. These builds require you to create something with minimal guidance outside of the documentation.

## Main Assignment

In this assignment, you will build a vector RAG application using LangChain v1, OpenAI embeddings, and Qdrant.

The main notebook is:

```text
01_Cat_Health_Vector_RAG_LangChain_Qdrant.ipynb
```

The notebook uses the bundled cat health guideline PDF in `data/cat_health_guidelines.pdf`.

### Setup

From this folder, install the environment with uv:

```bash
uv sync
```

Then open the notebook in Cursor or VS Code and select the Python/Jupyter environment created by uv.

You will also need an OpenAI API key available when running the notebook.

---

## 🏗️ Activity #1: Embedding Similarity

Run the embedding similarity primer in the notebook.

You will compare embeddings for terms like:

- `king`
- `queen`
- `banana`
- `cat`
- `veterinarian`
- `cat health guidelines`

#### ❓Question #1

Why is cosine similarity useful for dense vector retrieval?

##### ✅ Answer:

---

## 🏗️ Activity #2: Build the Vector RAG Pipeline

Run the notebook sections that:

1. Load the PDF into LangChain `Document` objects
2. Split the document into chunks
3. Embed the chunks
4. Store the chunk embeddings in in-memory Qdrant
5. Retrieve relevant chunks with similarity scores
6. Generate an answer grounded in retrieved context

#### ❓Question #2

Why is metadata important for a RAG application?

##### ✅ Answer:

Well typically the metadata is the data most people care about, since the data in the RAG application is just an embedding. But beyond that technicality, we often want to give references or sources back to the user so they can confirm and gain confidence in our answers since LLMs are known to hallucinate.

#### ❓Question #3

What tradeoff do we make when choosing chunk size and chunk overlap?

##### ✅ Answer:

A chunk size of 1 token has lost all context, but a chunk size of 1_000_000+ will contain so much context it has ceased to be useful. Somewhere in between is an optimal chunk size, and it's different for each dataset, but it typically is between 400-800 tokens or about the size of 1 to 2 paragraphs. Essentially, we are looking for each chunk to contain an idea.

For chunk overlap, the larger a chunk size the more duplication we will have in our database so we want them as small as possible to stay efficient. The smaller a chunk size, the more we rely on getting lucky that we have optimal splits. We are trying to prevent cutting off sentences in the middle, or paragraphs in the middle, etc. Situations where a single idea could be split into two seperate chunks and prevent either of them from surfacing during search.

Use the [Chunk Visualizer](https://chunkviz.up.railway.app/) to experiment with different chunk sizes and overlaps and see how the text boundaries change.

#### ❓Question #4

What does a similarity score help you understand, and what does it not prove by itself?

##### ✅ Answer:

That the query and the response are either close or far apart in the latent space. Typically it means they are going to have similar word choices, in similar orders. It doesn't really prove anything, so there's many things I could answer here, but this seems like a leading question in which case I'll answer it doesn't prove that the result from the query contains the answer to the user's question.

---

## 🏗️ Activity #3: Vibe Check Retrieval Quality

Run the notebook's vibe check queries and inspect both:

- The retrieved context
- The generated answer

#### ❓Question #5

For the vibe check queries, did the retrieved context seem relevant before generation? Why or why not?

##### ✅ Answer:

We didn't print the retrieved context, but based on the references cited, and content it seems like we have copied some of the phrases from the pdf word for word and they are relevant. So yes. The last vibe check question is the most interesting, it recieved 4 chunks but still answered correctly.

---

## 🏗️ Activity #4: Tune Retrieval

Improve retrieval quality by changing one or more of:

- Chunk size
- Chunk overlap
- Retrieval `k`
- Query wording

Document what changed and whether retrieval improved.

##### Settings Changed:

- chunk_size, chunk_overlap, and `top_k`, swept jointly using AutoRAG.
- Sweep grid: chunk_size ∈ {500, 1000, 1500} × chunk_overlap ∈ {100, 200, 300} (paired, 1:5 ratio) × top_k ∈ {2, 4, 6}, evaluated against a 5-question gold QA set with one ground-truth chunk per question (anchored on a distinctive phrase).

**Leaderboard (sorted by retrieval_ndcg):**

| chunk_size | overlap | top_k | recall | precision | F1   | NDCG | MRR  |
|-----------:|--------:|------:|-------:|----------:|-----:|-----:|-----:|
| **500**    | **100** | **2** | 1.00   | 0.50      | 0.67 | 1.00 | 1.00 |
| 500        | 100     | 4     | 1.00   | 0.25      | 0.40 | 1.00 | 1.00 |
| 500        | 100     | 6     | 1.00   | 0.17      | 0.29 | 1.00 | 1.00 |
| 1000       | 200     | 4     | 1.00   | 0.25      | 0.40 | 0.89 | 0.85 |
| 1000       | 200     | 6     | 1.00   | 0.17      | 0.29 | 0.89 | 0.85 |
| 1000       | 200     | 2     | 0.80   | 0.40      | 0.53 | 0.80 | 0.80 |
| 1500       | 300     | 2     | 0.80   | 0.40      | 0.53 | 0.80 | 0.80 |
| 1500       | 300     | 4     | 0.80   | 0.20      | 0.32 | 0.80 | 0.80 |
| 1500       | 300     | 6     | 0.80   | 0.13      | 0.23 | 0.80 | 0.80 |

**Headline:** all three `chunk_size=500, overlap=100` runs score **NDCG 1.00 + MRR 1.00** — the gold chunk is always ranked #1. The 500/100/`top_k=2` row wins on F1 because precision is highest there.

**Before:** notebook default of `chunk_size=1000, chunk_overlap=200, k=4` → recall 1.00, NDCG 0.89, MRR 0.85.

**After:** `chunk_size=500, chunk_overlap=100, top_k=2` → recall 1.00, NDCG 1.00 (+12%), MRR 1.00 (+18%), F1 0.67 (+67% vs the default's 0.40). Smaller chunks make the answer-bearing chunk topically pure, so it ranks #1 reliably; smaller `top_k` then captures the precision win without losing recall.

##### Results:

Yes, retrieval improved decisively. Three observations from the table:

1. **`top_k` doesn't change retrieval ranking quality, only precision.** Recall, NDCG, and MRR are flat across `top_k` for any fixed (chunk_size, overlap). That makes sense — the retriever returns the same top-K *ordering*; cranking K just dilutes precision by adding lower-ranked passages.
2. **Smaller chunks dominate.** 500-char chunks land the gold chunk at rank 1 every time (NDCG=MRR=1.0). 1000-char chunks miss rank 1 on at least one question, so MRR drops to ~0.85. 1500-char chunks dilute the embedding enough that one question's gold chunk never appears at all (recall=0.80 across all top_k).
3. **Overlap didn't earn its keep here.** A larger overlap was supposed to protect against unlucky boundary splits, but at 1500/300 we still lost a question's gold chunk. The hypothesis is that on this PDF the relevant phrase-cluster fits inside a 500-char window, so giving the embedder more text only adds neighboring topics that pull the cosine direction off-target.

**Caveats:**
- 5 QA pairs is a small N — recall jumps in 0.20 increments, so anything that swings one question swings the whole metric. A more rigorous sweep would use ≥30 questions or AutoRAG's own QA-generation (`autorag.data.qa.*`) to scale the gold set.
- The `retrieval_gt` is one-chunk-per-question, anchored on a specific phrase. Questions whose answer genuinely spans multiple chunks aren't measured here.
- We swept chunk_size and overlap together (1:5 ratio). Decoupling them — e.g., 500/0 vs 500/100 vs 500/200 — would tell us which one is doing the work.

---

## Optional Deep Dive: RAG From Scratch

If you want to look underneath the library abstractions, run the optional reference notebook:

```text
02_Cat_Health_Vector_RAG_From_Scratch.ipynb
```

It builds the same retrieval pipeline again with only:

- `pypdf` for extracting text from the PDF
- Python standard-library HTTP requests for calling OpenAI
- Handcrafted document, chunking, embedding, similarity-search, vector-store, and generation primitives

This notebook is a reference walkthrough, not an additional assignment. Its purpose is to make the responsibilities hidden by LangChain, Qdrant, and provider SDKs visible.

---

## Submitting Your Homework

### Main Assignment

Follow these steps to prepare and submit your homework:

1. Pull the latest updates from upstream into the main branch of your AIE9 repo:

```bash
git checkout main
git pull upstream main
git push origin main
```

2. Start Cursor from the `01_Dense_Vector_Retrieval` folder.
3. Complete the notebook.
4. Answer the questions in this `README.md`.
5. Add, commit, and push your modified work to your origin repository.

When submitting your homework, provide the GitHub URL to your AIE9 repo.
