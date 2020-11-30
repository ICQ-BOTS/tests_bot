box.cfg {
    listen = 3301
}

box.schema.user.grant('guest', 'read,write,execute', 'universe', nil, { if_not_exists = true })
box.schema.user.passwd('pass')


function init()

--------------------------------Users--------------------------------

if box.space.users == nil then
	local users = box.schema.space.create('users', { if_not_exists = true })
	
	users:format({
		{ name = 'user_id', 	type = 'string' },
		{ name = 'permissions', type = 'unsigned' }
	})


	users:create_index('primary', { type = 'hash', parts = { 'user_id' }, if_not_exists = true, unique = true })
	users:create_index('secondary', { type = 'tree', parts = { 'permissions' }, if_not_exists = true, unique = false })
	
end

--------------------------------Tests--------------------------------

if box.space.tests == nil then
	local tests = box.schema.space.create('tests', { if_not_exists = true })
	
	tests:format({
		{ name = 'id', 				type = 'integer'	},	--0
		{ name = 'name', 			type = 'string'		},  --1
		{ name = 'handle_module', 	type = 'string'		},  --2
		{ name = 'publicsh_status', type = 'integer'	} 	--3
	})
	
	if box.sequence.tests_ids_autoinc == nil then
		box.schema.sequence.create('tests_ids_autoinc', {start=1, min=1, cycle=false, step=1 })
	end
	
	tests:create_index('primary', { type = 'hash', parts = { 'id' }, sequence = 'tests_ids_autoinc', unique = true })
end

--------------------------------Questions--------------------------------

if box.space.questions == nil then
	local questions = box.schema.space.create('questions', { if_not_exists = true })
	questions:format({
		{ name = 'id', 		type = 'integer'	},	--0
		{ name = 'test_id', type = 'integer'	},	--1
		{ name = 'text', 	type = 'string'		},	--2
		{ name = 'image', 	type = 'string'		}	--3
	})
	
	if box.sequence.questions_ids_autoinc == nil then
		box.schema.sequence.create('questions_ids_autoinc', {start=1, min=1, cycle=false, step=1 })
	end
	
	questions:create_index('primary', { type = 'hash', parts = { 'id' }, sequence = 'questions_ids_autoinc', unique = true })
	questions:create_index('test_index', { type = 'tree', parts = { 'test_id' }, unique = false })
end

--------------------------------Tests results--------------------------------

if box.space.tests_results == nil then
	local tests_results = box.schema.space.create('tests_results', { if_not_exists = true })
	tests_results:format({
		{ name = 'id', 		type = 'integer'	},	--0
		{ name = 'test_id', type = 'integer'	},	--1
		{ name = 'text', 	type = 'string'		},	--2
		{ name = 'image', 	type = 'string'		},	--3
		{ name = 'value', 	type = 'string'		}	--4
	})
	
	if box.sequence.tests_results_ids_autoinc == nil then
		box.schema.sequence.create('tests_results_ids_autoinc', {start=1, min=1, cycle=false, step=1 })
	end
	
	tests_results:create_index('primary', { type = 'hash', parts = { 'id' }, sequence = 'tests_results_ids_autoinc', unique = true })
	tests_results:create_index('test_index', { type = 'tree', parts = { 'test_id' }, unique = false })
end

--------------------------------Answers--------------------------------

if box.space.answers == nil then
	local answers = box.schema.space.create('answers', { if_not_exists = true })
	answers:format({
		{ name = 'id', 			type = 'integer'	},	--0
		{ name = 'question_id', type = 'integer'	},	--1
		{ name = 'text', 		type = 'string'		},	--2
		{ name = 'image', 		type = 'string'		},	--3
		{ name = 'value', 		type = 'string'		}	--4
	})
	
	if box.sequence.answers_ids_autoinc == nil then
		box.schema.sequence.create('answers_ids_autoinc', {start=1, min=1, cycle=false, step=1 })
	end
	
	answers:create_index('primary', { type = 'hash', parts = { 'id' }, sequence = 'answers_ids_autoinc', unique = true })
	answers:create_index('question_index', { type = 'tree', parts = { 'question_id' }, unique = false })
end

if box.space.completed_tests == nil then
	local completed_tests = box.schema.space.create('completed_tests', { if_not_exists = true })
	completed_tests:format({
		{ name = 'user_id',		type = 'string'		},	--0
		{ name = 'test_id', 	type = 'integer'	},	--1
		{ name = 'count', 		type = 'integer'	}	--2
	})

	
	completed_tests:create_index('primary', { type = 'hash', parts = { 'user_id', 'test_id' }, unique = true })
	completed_tests:create_index('user_id_index', { type = 'tree', parts = { 'user_id' }, unique = false })
	completed_tests:create_index('test_id_index', { type = 'tree', parts = { 'test_id' }, unique = false })
end

end

function add_test(name)
	return box.space.tests:insert{box.NULL, name, 'default', 0}
end

function add_question(testId, text, image)
	return box.space.questions:insert{box.NULL, testId, text, image}
end

function add_answer(questionId, text, image, value)
	return box.space.answers:insert{box.NULL, questionId, text, image, value}
end

function add_test_result(testId, text, image, value)
	return box.space.tests_results:insert{box.NULL, testId, text, image, value}
end

function reinit()
	reinitArray = { 
		--box.space.users, 
		--box.space.tests, 
		--box.sequence.tests_ids_autoinc, 
		--box.space.questions, 
		--box.sequence.questions_ids_autoinc, 
		--box.space.tests_results,
		--box.sequence.tests_results_ids_autoinc, 
		--box.space.answers,
		--box.sequence.answers_ids_autoinc,
		box.space.completed_tests
	}
	for key, value in pairs(reinitArray) do
		if value ~= nil then
			value:drop()
		end
	end
	
	
	init()
end

--reinit()

box.once("data", init)